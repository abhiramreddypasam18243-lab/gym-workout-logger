"""Authentication routes (spec §7, §10, AC-01–07)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    client_host,
    get_current_session,
    request_is_tls,
    verify_csrf,
    verify_tls_for_login,
)
from app.config import get_settings
from app.database import get_db
from app.models.user import Session, User, UserFoodConstraint, UserProfile
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.security import (
    DUMMY_PASSWORD_HASH,
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_token,
    login_rate_limiter,
    validate_password_length,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Register a new user account (spec §7, §10, AC-01, AC-02, AC-09)."""
    if not settings.REGISTRATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "registration_disabled",
                "message": "Registration is currently disabled",
            },
        )

    # Validate password length (AC-02: 12-128 chars)
    if not validate_password_length(payload.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_password_length",
                "message": "Password must be 12 to 128 characters",
            },
        )

    normalized_email = payload.email.lower()

    # Case-insensitive duplicate email check (AC-01)
    stmt = select(User).where(User.email == normalized_email)
    existing = await db.scalar(stmt)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_taken", "message": "An account with this email already exists"},
        )

    # Hash password with Argon2id (AC-01)
    pwd_hash = hash_password(payload.password)

    user = User(
        email=normalized_email,
        password_hash=pwd_hash,
    )
    db.add(user)
    await db.flush()

    # Create associated profile
    profile = UserProfile(
        user_id=user.id,
        display_name=payload.display_name or normalized_email.split("@")[0],
    )
    db.add(profile)
    # Default exclusions (D-27): a normal, removable excluded-ingredient preference
    for ingredient in settings.DEFAULT_EXCLUDED_INGREDIENTS:
        db.add(
            UserFoodConstraint(
                user_id=user.id,
                constraint_type="excluded_ingredient",
                constraint_value=ingredient.strip().lower(),
            )
        )
    await db.commit()
    await db.refresh(user)

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": profile.display_name,
            "is_active": user.is_active,
        }
    }


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Sign in and establish revocable session (spec SEC2, SEC5, SEC6, SEC7, AC-03, AC-04, AC-07)."""
    # Enforce TLS for non-localhost clients (AC-07)
    verify_tls_for_login(request)

    normalized_email = payload.email.lower()
    client_ip = client_host(request)
    rate_limit_key = f"{normalized_email}:{client_ip}"

    # Rate limiting check (AC-04: max 5 failed attempts per 15 min)
    is_limited, retry_after = login_rate_limiter.is_rate_limited(rate_limit_key)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
            detail={
                "code": "rate_limited",
                "message": "Too many failed login attempts. Try again later.",
            },
        )

    # Lookup user
    stmt = select(User).options(selectinload(User.profile)).where(User.email == normalized_email)
    user = await db.scalar(stmt)

    if not user:
        # Constant-time mitigation against user enumeration (SEC5, AC-03)
        verify_password(payload.password, DUMMY_PASSWORD_HASH)
        login_rate_limiter.record_failure(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid email or password"},
        )

    if not verify_password(payload.password, user.password_hash):
        login_rate_limiter.record_failure(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Invalid email or password"},
        )

    # Clear rate limiter on successful authentication
    login_rate_limiter.clear(rate_limit_key)

    # Create server-side session (SEC2, AC-03)
    raw_token = generate_session_token()
    raw_csrf = generate_csrf_token()

    now = datetime.now(UTC)
    expires = now + timedelta(days=settings.SESSION_LIFETIME_DAYS)

    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        created_at=now,
        expires_at=expires,
    )
    db.add(session)
    await db.commit()

    is_secure = request_is_tls(request)

    # Set HttpOnly, SameSite=Lax session cookie
    response.set_cookie(
        key="session_id",
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        expires=int(expires.timestamp()),
        path="/",
    )

    # Set client-readable CSRF cookie
    response.set_cookie(
        key="csrf_token",
        value=raw_csrf,
        httponly=False,
        samesite="lax",
        secure=is_secure,
        expires=int(expires.timestamp()),
        path="/",
    )

    display_name = user.profile.display_name if user.profile else user.email.split("@")[0]

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": display_name,
            "is_active": user.is_active,
        },
        "csrf_token": raw_csrf,
    }


@router.post("/logout")
async def logout(
    response: Response,
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    _csrf: Annotated[None, Depends(verify_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Revoke session and clear cookies (spec SEC2, AC-05, AC-06)."""
    _user, session = auth
    session.revoked_at = datetime.now(UTC)
    await db.commit()

    response.delete_cookie(key="session_id", path="/")
    response.delete_cookie(key="csrf_token", path="/")

    return {"message": "Logged out successfully"}


@router.get("/me")
async def me(
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
) -> dict[str, Any]:
    """Return currently authenticated user (spec §7)."""
    user, _session = auth
    display_name = user.profile.display_name if user.profile else user.email.split("@")[0]

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": display_name,
            "is_active": user.is_active,
        }
    }
