"""Tests for authentication — password hashing, JWT, and auth endpoints.

Uses aiosqlite in-memory database and a real FastAPI test client.
No mocks — all operations hit the actual auth module and SQLAlchemy repos.
"""

from __future__ import annotations

import os
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-not-real")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")

from medai.api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from medai.config import get_settings
from medai.domain.entities import User, UserRole
from medai.repositories.database import get_db_session
from medai.repositories.models import Base
from medai.repositories.sqlalchemy import SqlAlchemyUserRepository


# ═══════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
        await sess.rollback()


@pytest_asyncio.fixture
async def test_app(engine):
    """Create a FastAPI test app with overridden DB session."""
    from medai.main import app

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_app):
    """Async HTTP client for the test app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_user(session) -> User:
    """Create a test user in the DB and return the entity."""
    repo = SqlAlchemyUserRepository(session)
    user = User(
        email="testdoc@hospital.com",
        hashed_password=hash_password("securepass123"),
        name="Dr. Test",
        role=UserRole.DOCTOR,
    )
    await repo.create(user)
    await session.commit()
    return user


# ═══════════════════════════════════════════════════════════════
#  Password Hashing Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_password_returns_hash(self):
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert hashed.startswith("$2")  # bcrypt prefix ($2b$ or $2a$)

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # bcrypt salts should differ


# ═══════════════════════════════════════════════════════════════
#  JWT Token Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestJWT:
    def test_create_access_token(self):
        settings = get_settings()
        token = create_access_token({"sub": "USR-12345678"})
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "USR-12345678"
        assert "exp" in payload

    def test_token_with_custom_expiry(self):
        settings = get_settings()
        token = create_access_token(
            {"sub": "USR-12345678"},
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "USR-12345678"

    def test_token_with_extra_claims(self):
        settings = get_settings()
        token = create_access_token({"sub": "USR-12345678", "role": "doctor"})
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["role"] == "doctor"


# ═══════════════════════════════════════════════════════════════
#  Auth Endpoint Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
@pytest.mark.asyncio
class TestRegisterEndpoint:
    async def test_register_success(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "strongpass123",
            "name": "New User",
            "role": "doctor",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert data["user"]["email"] == "new@example.com"
        assert data["user"]["role"] == "doctor"

    async def test_register_duplicate_email(self, client):
        payload = {
            "email": "dup@example.com",
            "password": "pass123",
            "name": "User",
            "role": "doctor",
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        resp2 = await client.post("/api/v1/auth/register", json=payload)
        assert resp2.status_code == 409

    async def test_register_invalid_role(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "bad@example.com",
            "password": "pass",
            "name": "User",
            "role": "superadmin",
        })
        assert resp.status_code == 422

    async def test_register_missing_fields(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "partial@example.com",
        })
        assert resp.status_code == 422


@pytest.mark.unit
@pytest.mark.asyncio
class TestLoginEndpoint:
    async def test_login_success(self, client):
        # First register
        await client.post("/api/v1/auth/register", json={
            "email": "login@test.com",
            "password": "mypass123",
            "name": "Login User",
            "role": "doctor",
        })
        # Then login
        resp = await client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "mypass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert data["user"]["email"] == "login@test.com"

    async def test_login_wrong_password(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "wrongpw@test.com",
            "password": "correct",
            "name": "User",
            "role": "doctor",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "email": "wrongpw@test.com",
            "password": "incorrect",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "anything",
        })
        assert resp.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
class TestMeEndpoint:
    async def test_me_authenticated(self, client):
        # Register and get token
        reg = await client.post("/api/v1/auth/register", json={
            "email": "me@test.com",
            "password": "pass123",
            "name": "Me User",
            "role": "admin",
        })
        token = reg.json()["access_token"]

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@test.com"
        assert data["name"] == "Me User"
        assert data["role"] == "admin"

    async def test_me_no_token(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
class TestProtectedEndpoints:
    """Verify that patient/case endpoints reject unauthenticated requests."""

    async def test_patients_list_requires_auth(self, client):
        resp = await client.get("/api/v1/patients")
        assert resp.status_code == 401

    async def test_patient_detail_requires_auth(self, client):
        resp = await client.get("/api/v1/patients/PT-1")
        assert resp.status_code == 401

    async def test_analyze_requires_auth(self, client):
        resp = await client.post("/api/v1/cases/analyze", json={})
        assert resp.status_code == 401
