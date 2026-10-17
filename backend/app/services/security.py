"""Security services: Argon2id password hashing, session tokens, CSRF tokens, and rate limiting.

Spec requirements:
- SEC1: Argon2id hashing, 12-128 chars (AC-01, AC-02).
- SEC2: Server-side revocable sessions (AC-03, AC-05).
- SEC3: Double-submit CSRF protection (AC-06).
- SEC5: Constant-time authentication / dummy hash (AC-03).
- SEC6: Rate limiting failed logins (AC-04).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Password hasher configured for Argon2id (spec SEC1, AC-01)
_ph = PasswordHasher()

# Pre-computed dummy Argon2id hash for constant-time check on unknown emails (SEC5, AC-03)
DUMMY_PASSWORD_HASH = _ph.hash("dummy_constant_time_timing_mitigation_password")


def hash_password(password: str) -> str:
    """Hash password using Argon2id.

    Result starts with $argon2id$ (spec SEC1, AC-01).
    """
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash in constant time."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def validate_password_length(password: str) -> bool:
    """Validate password length: minimum 12, maximum 128 characters (spec SEC1, AC-02)."""
    return 12 <= len(password) <= 128


def generate_session_token() -> str:
    """Generate high-entropy random URL-safe session token."""
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """Generate high-entropy random URL-safe CSRF token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash token with SHA-256 for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LoginRateLimiter:
    """In-memory rate limiter for failed login attempts with clock injection (spec SEC6, AC-04).

    At most 5 failed attempts per account/IP within 15 minutes.
    6th failed attempt returns 429 with Retry-After.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # key -> list of attempt timestamps
        self._attempts: dict[str, list[datetime]] = {}

    def record_failure(self, key: str, now: datetime | None = None) -> None:
        current_time = now if now is not None else datetime.now(UTC)
        if key not in self._attempts:
            self._attempts[key] = []
        self._attempts[key].append(current_time)

    def is_rate_limited(self, key: str, now: datetime | None = None) -> tuple[bool, int]:
        """Check if key is rate limited.

        Returns (is_limited, retry_after_seconds).
        """
        current_time = now if now is not None else datetime.now(UTC)
        cutoff = current_time - timedelta(seconds=self.window_seconds)

        if key not in self._attempts:
            return False, 0

        # Filter out timestamps outside window
        active_attempts = [t for t in self._attempts[key] if t > cutoff]
        self._attempts[key] = active_attempts

        if len(active_attempts) >= self.max_attempts:
            oldest_active = min(active_attempts)
            remaining = int(
                (
                    oldest_active + timedelta(seconds=self.window_seconds) - current_time
                ).total_seconds()
            )
            return True, max(1, remaining)

        return False, 0

    def clear(self, key: str) -> None:
        """Clear rate limit history on successful login."""
        self._attempts.pop(key, None)


# Default global rate limiter instance
login_rate_limiter = LoginRateLimiter()
