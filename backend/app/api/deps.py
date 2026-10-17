"""FastAPI authentication, session, CSRF, and TLS dependencies (spec §7, §10, AC-03–07)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import Session, User
from app.services.security import hash_token


async def get_current_session(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[User, Session]:
    """Retrieve authenticated user and active session from cookie (spec SEC2, AC-03, AC-05)."""
    raw_token = request.cookies.get("session_id")
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "Sign in required"},
        )

    token_hash = hash_token(raw_token)
    now = datetime.now(UTC)

    stmt = (
        select(Session)
        .options(selectinload(Session.user).selectinload(User.profile))
        .where(
            Session.token_hash == token_hash,
            Session.revoked_at.is_(None),
            Session.expires_at > now,
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session or not session.user or not session.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_session", "message": "Session expired or invalid"},
        )

    return session.user, session


async def get_current_user(
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
) -> User:
    """Convenience dependency returning only the User."""
    return auth[0]


async def verify_csrf(
    request: Request,
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
) -> None:
    """Verify CSRF token for state-changing requests (spec SEC3, AC-06).

    Exempts GET requests. Checks X-CSRF-Token header against session's csrf_token_hash.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    _user, session = auth
    header_csrf = request.headers.get("X-CSRF-Token")
    if not header_csrf:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "csrf_failed", "message": "CSRF token missing"},
        )

    if hash_token(header_csrf) != session.csrf_token_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "csrf_failed", "message": "CSRF token invalid"},
        )


def verify_tls_for_login(request: Request) -> None:
    """Enforce TLS for non-localhost clients on credential endpoints (spec SEC7, AC-07)."""
    client_host = request.client.host if request.client else "127.0.0.1"
    localhost_hosts = {"127.0.0.1", "::1", "localhost", "testclient"}

    if client_host in localhost_hosts:
        return

    # Non-localhost client: must be over HTTPS or valid proxy HTTPS
    scheme = request.url.scheme
    forwarded_proto = request.headers.get("X-Forwarded-Proto")

    # In production with trusted reverse proxy, X-Forwarded-Proto is checked
    scheme = request.scope.get("scheme") or request.url.scheme
    is_tls = scheme == "https" or forwarded_proto == "https"

    if not is_tls:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "tls_required",
                "message": "Credentials accepted only over TLS for remote clients",
            },
        )
