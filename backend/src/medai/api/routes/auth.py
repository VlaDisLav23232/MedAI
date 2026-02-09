"""Authentication endpoints — login, register, current user.

Contract matches what the frontend expects:
- POST /auth/login  → {access_token, token_type, user: {id, email, name, role}}
- POST /auth/register → same
- GET  /auth/me → {id, email, name, role}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from medai.api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from medai.domain.entities import User, UserRole
from medai.domain.interfaces import BaseUserRepository
from medai.domain.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from medai.repositories.database import get_db_session
from medai.repositories.sqlalchemy import SqlAlchemyUserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_user_repo(session: AsyncSession = Depends(get_db_session)) -> BaseUserRepository:
    return SqlAlchemyUserRepository(session)


def _user_response(user: User) -> UserResponse:
    """Map domain User to public UserResponse."""
    role_value = user.role.value if isinstance(user.role, UserRole) else user.role
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=role_value,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    user_repo: BaseUserRepository = Depends(_get_user_repo),
) -> AuthResponse:
    """Authenticate with email + password, receive JWT token."""
    user = await user_repo.get_by_email(body.email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(data={"sub": user.id})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_user_response(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    user_repo: BaseUserRepository = Depends(_get_user_repo),
) -> AuthResponse:
    """Create a new user account and return JWT token."""
    # Check if email already registered
    existing = await user_repo.get_by_email(body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Validate role
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{body.role}'. Must be one of: doctor, admin, nurse",
        )

    # Create user
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        role=role,
    )
    created = await user_repo.create(user)

    token = create_access_token(data={"sub": created.id})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_user_response(created),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return _user_response(current_user)


@router.post("/logout", status_code=200)
async def logout() -> dict[str, str]:
    """Logout endpoint (JWT is stateless — client clears the token)."""
    return {"detail": "Logged out"}
