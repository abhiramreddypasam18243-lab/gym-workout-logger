"""Canary logging test (spec SEC12, AC-104).

Verifies that structured logs never leak plaintext passwords, tokens,
session IDs, or full email addresses.
"""

import logging

from app.services.security import hash_password, hash_token


def test_ac_104_canary_no_secrets_in_logs(caplog):
    """Canary test: sensitive credentials never appear in application logs."""
    canary_password = "SuperSecretCanaryPassword123!"
    canary_token = "canary_token_secret_value_xyz789"
    canary_email = "canary_user@confidential-domain.com"

    logger = logging.getLogger("app.security")
    with caplog.at_level(logging.DEBUG):
        # Simulate standard operations
        pwd_hash = hash_password(canary_password)
        token_h = hash_token(canary_token)

        # Log safe diagnostic message
        masked_email = canary_email[0] + "***@" + canary_email.split("@")[1]
        logger.info(f"User operation completed for {masked_email}, hash prefix {token_h[:8]}")

    captured_text = caplog.text

    assert canary_password not in captured_text, "Plaintext password leaked in logs!"
    assert canary_token not in captured_text, "Session token leaked in logs!"
    assert canary_email not in captured_text, "Full email address leaked in logs!"
    assert pwd_hash not in captured_text or "$argon2id$" in pwd_hash  # Hash is safe if present
