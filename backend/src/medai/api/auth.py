"""Authentication utilities — JWT tokens, password hashing, FastAPI dependencies.

Provides:
- Password hashing/verification via bcrypt
- JWT creation and validation
- `get_current_user` dependency for route protection
- `require_role` dependency factory for role-based access control
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import bcrypt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from medai.config import get_settings
from medai.domain.entities import User
from medai.repositories.database import get_db_session
from medai.repositories.sqlalchemy import SqlAlchemyUserRepository

logger = structlog.get_logger()

# ── Password hashing ──────────────────────────────────────


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT tokens ─────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    to_encode["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


# ── FastAPI dependencies ───────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Decode JWT and return the authenticated user.

    Raises 401 if token is invalid, expired, or user not found.
    """
    logger.info("get_current_user_called", token_prefix=token[:20] if token else "None")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        logger.info("jwt_decoded", user_id=user_id, payload_keys=list(payload.keys()))
        if user_id is None:
            logger.warning("jwt_missing_sub")
            raise credentials_exception
    except JWTError as e:
        logger.error("jwt_decode_error", error=str(e))
        raise credentials_exception

    user_repo = SqlAlchemyUserRepository(session)
    user = await user_repo.get_by_id(user_id)
    
    logger.info("user_lookup", user_id=user_id, found=user is not None, is_active=user.is_active if user else None)

    if user is None or not user.is_active:
        logger.warning("user_not_found_or_inactive", user_id=user_id)
        raise credentials_exception

    logger.info("auth_success", user_id=user_id, user_email=user.email)
    return user


def require_role(*roles: str):
    """Dependency factory — restricts endpoint to specific user roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def _check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not authorized. Required: {', '.join(roles)}",
            )
        return current_user
    return _check_role
