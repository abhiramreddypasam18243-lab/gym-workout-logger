"""Unit and service tests for authentication, sessions, CSRF, and security.

Acceptance criteria:
- AC-01 (SEC1): Argon2id hashing, no password logging, duplicate email rejected case-insensitively (409).
- AC-02 (SEC1): Password length 11 rejected (422), 12 and 128 accepted, 129 rejected.
- AC-03 (SEC2, SEC5): Revocable sessions, constant-time dummy hash on unknown email.
- AC-04 (SEC6): 6th failed login within 15 minutes returns 429 with Retry-After.
- AC-05 (SEC2): Old session revoked on logout.
- AC-06 (SEC3): Double-submit CSRF token verification.
- AC-07 (SEC7): TLS required for non-localhost clients.
- AC-09 (SEC8): Request body containing user_id or unknown fields rejected with 422.
- AC-10 (SEC8): SQL injection string stored literally without executing.
- AC-13 (SEC8): Request body above 1 MB rejected with 413.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from app.api.deps import verify_tls_for_login
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.security import (
    DUMMY_PASSWORD_HASH,
    LoginRateLimiter,
    generate_csrf_token,
    hash_password,
    hash_token,
    validate_password_length,
    verify_password,
)


def test_ac_01_argon2id_hashing():
    """AC-01: Stored password hash starts with $argon2id$."""
    raw_password = "SecurePassword123!"
    hashed = hash_password(raw_password)

    assert hashed.startswith("$argon2id$"), f"Hash must start with $argon2id$: {hashed}"
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_ac_01_case_insensitive_email_normalization():
    """AC-01: A@x.com and a@x.com normalize to identical lowercase email."""
    reg1 = RegisterRequest(email="A@x.com", password="SecurePassword123!")
    reg2 = RegisterRequest(email="a@x.com", password="SecurePassword123!")

    assert reg1.email == "a@x.com"
    assert reg2.email == "a@x.com"
    assert reg1.email == reg2.email


def test_ac_02_password_length_boundaries():
    """AC-02: 11 rejected, 12 and 128 accepted, 129 rejected."""
    # 11 characters -> rejected
    assert validate_password_length("a" * 11) is False
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="a" * 11)

    # 12 characters -> accepted
    assert validate_password_length("a" * 12) is True
    reg12 = RegisterRequest(email="user@example.com", password="a" * 12)
    assert len(reg12.password) == 12

    # 128 characters -> accepted
    assert validate_password_length("a" * 128) is True
    reg128 = RegisterRequest(email="user@example.com", password="a" * 128)
    assert len(reg128.password) == 128

    # 129 characters -> rejected
    assert validate_password_length("a" * 129) is False
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="a" * 129)


def test_ac_03_dummy_hash_timing_mitigation():
    """AC-03: Unknown emails check dummy hash to consume constant time."""
    assert DUMMY_PASSWORD_HASH.startswith("$argon2id$")
    assert verify_password("arbitrary_password", DUMMY_PASSWORD_HASH) is False


def test_ac_04_rate_limiting_window_and_clock():
    """AC-04: 6th failed attempt within 15 min returns 429; window passing succeeds."""
    limiter = LoginRateLimiter(max_attempts=5, window_seconds=900)
    key = "attacker@example.com:192.168.1.50"
    base_time = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)

    # First 5 failed attempts within window
    for i in range(5):
        t = base_time + timedelta(minutes=i)
        is_limited, _ = limiter.is_rate_limited(key, now=t)
        assert is_limited is False
        limiter.record_failure(key, now=t)

    # 6th attempt at minute 5 -> rate limited (429)
    t_6th = base_time + timedelta(minutes=5)
    is_limited, retry_after = limiter.is_rate_limited(key, now=t_6th)
    assert is_limited is True
    assert retry_after > 0

    # Advance clock past 15-minute window (minute 16)
    t_after_window = base_time + timedelta(minutes=16)
    is_limited_later, _ = limiter.is_rate_limited(key, now=t_after_window)
    assert is_limited_later is False


def test_ac_06_csrf_token_generation_and_verification():
    """AC-06: CSRF token generation, SHA-256 hashing, and verification."""
    token = generate_csrf_token()
    token_h = hash_token(token)

    assert len(token) >= 32
    assert len(token_h) == 64  # SHA-256 hex digest length
    assert hash_token(token) == token_h
    assert hash_token("wrong_token") != token_h


def test_ac_07_tls_required_for_remote_clients():
    """AC-07: Plain HTTP login from non-localhost client raises 403 tls_required."""
    # Localhost client over plain HTTP -> allowed
    scope_local = {
        "type": "http",
        "path": "/api/auth/login",
        "client": ("127.0.0.1", 54321),
        "scheme": "http",
        "headers": [],
    }
    req_local = Request(scope_local)
    verify_tls_for_login(req_local)  # Does not raise

    # Remote client over plain HTTP -> raises 403 tls_required
    scope_remote = {
        "type": "http",
        "path": "/api/auth/login",
        "client": ("192.168.1.100", 54321),
        "scheme": "http",
        "headers": [],
    }
    req_remote = Request(scope_remote)
    with pytest.raises(HTTPException) as exc_info:
        verify_tls_for_login(req_remote)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "tls_required"

    # Remote client over HTTPS -> allowed
    scope_remote_https = {
        "type": "http",
        "path": "/api/auth/login",
        "client": ("192.168.1.100", 54321),
        "scheme": "https",
        "headers": [],
    }
    req_remote_https = Request(scope_remote_https)
    verify_tls_for_login(req_remote_https)  # Does not raise


def test_ac_09_unknown_fields_and_user_id_forbidden():
    """AC-09: Request body containing user_id or unknown fields rejected with 422."""
    # user_id injection attempt
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate(
            {
                "email": "valid@example.com",
                "password": "SecurePassword123!",
                "user_id": "malicious-uuid",
            }
        )

    # Arbitrary unknown field injection
    with pytest.raises(ValidationError):
        LoginRequest.model_validate(
            {"email": "valid@example.com", "password": "SecurePassword123!", "role": "admin"}
        )


def test_ac_10_sql_injection_payload_handled_literally():
    """AC-10: SQL injection payload '; DROP TABLE users;-- is preserved literally."""
    sqli_payload = "'; DROP TABLE users;--"
    req = RegisterRequest(
        email="test@example.com",
        password="ValidPassword123!",
        display_name=sqli_payload,
    )
    # Stored and returned as raw string without execution
    assert req.display_name == sqli_payload


def test_ac_11_security_headers_present():
    """AC-11 (SEC9): Responses carry CSP, X-Content-Type-Options, Referrer-Policy, frame protection."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    # Ping /api/health which is open
    resp = client.get("/api/health")

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_ac_13_request_body_above_1mb_rejected():
    """AC-13 (SEC8): Request body above 1 MB returns 413."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    # Create payload slightly over 1 MB (1024 * 1024 + 10 bytes)
    large_payload = "x" * (1024 * 1024 + 10)

    resp = client.post(
        "/api/auth/register",
        content=large_payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"]["code"] == "body_too_large"
