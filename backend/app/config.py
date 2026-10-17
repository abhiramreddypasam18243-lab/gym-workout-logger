"""Application configuration loaded from environment variables.

Safety thresholds are kept here in one place (ag.md safety rule).
All numeric values marked 'initial' in the spec are placeholders for review.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str

    # Security
    secret_key: str
    allowed_origin: str = "http://localhost:8080"
    environment: str = "development"
    trusted_proxy_ip: str = "127.0.0.1"

    # Feature flags
    registration_enabled: bool = True
    demo_mode: bool = False

    # Safety thresholds (initial values — review against qualified sources)
    # These are NOT authoritative; see spec section 3 and DECISIONS.md.
    estimate_floor_kcal: int = 1500
    plan_minimum_kcal: int = 1200

    # Session
    session_max_age_seconds: int = 86400 * 7  # 7 days

    # Rate limiting
    max_failed_logins: int = 5
    rate_limit_window_seconds: int = 900  # 15 minutes

    # Request limits
    max_body_size_bytes: int = 1_048_576  # 1 MB (SEC8)

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()  # type: ignore[call-arg]
