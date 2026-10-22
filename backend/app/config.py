"""Application configuration loaded from environment variables (spec SEC10, AC-12, AC-111).

Safety thresholds are kept here in one configuration module (ag.md safety rule).
All numeric values marked 'initial' in the spec are placeholders for review.
"""

from decimal import Decimal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding"}


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./gym_dev.db"
    )

    # Security (SEC10)
    SESSION_SECRET: str = Field(default="change-this-in-production-to-a-secure-random-string")
    SECRET_KEY: str | None = None
    ALLOWED_ORIGIN: str = "http://localhost:8080"
    ENVIRONMENT: str = "development"
    TRUSTED_PROXY_IP: str = "127.0.0.1"

    # Feature flags
    REGISTRATION_ENABLED: bool = True
    DEMO_MODE: bool = False

    # Excluded ingredients every new account starts with (D-27); users can remove them
    DEFAULT_EXCLUDED_INGREDIENTS: list[str] = ["beef"]

    # Safety thresholds (spec §3, D-16)
    ESTIMATE_FLOOR_KCAL: int = 1500
    PLAN_MINIMUM_KCAL: int = 1200

    # Progressive overload hint (D-33): placeholder step sizes for review, not coaching advice
    OVERLOAD_STEP_UPPER_KG: Decimal = Decimal("2.5")
    OVERLOAD_STEP_LOWER_KG: Decimal = Decimal("5")
    OVERLOAD_STEP_UPPER_LB: Decimal = Decimal("5")
    OVERLOAD_STEP_LOWER_LB: Decimal = Decimal("10")
    LOWER_BODY_MUSCLES: list[str] = ["quads", "hamstrings", "glutes", "calves"]
    DEFAULT_REP_MIN: int = 8
    DEFAULT_REP_MAX: int = 12

    # Session
    SESSION_LIFETIME_DAYS: int = 14
    SESSION_MAX_AGE_SECONDS: int = 86400 * 14

    # Rate limiting (SEC6)
    MAX_FAILED_LOGINS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 900  # 15 minutes

    # Request limits (SEC8)
    MAX_BODY_SIZE_BYTES: int = 1_048_576  # 1 MB

    # Compatibility properties
    @property
    def database_url(self) -> str:
        """Async driver URL. libpq-only options (sslmode, channel_binding), which hosted
        providers such as Neon add, are removed; SSL goes through database_connect_args."""
        url = (self.DATABASE_URL or "").strip()
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        base, _, query = url.partition("?")
        kept = [p for p in query.split("&") if p and p.split("=", 1)[0] not in _LIBPQ_ONLY_PARAMS]
        return base + ("?" + "&".join(kept) if kept else "")

    @property
    def database_connect_args(self) -> dict[str, str]:
        """asyncpg's equivalent of the URL's sslmode (e.g. Neon requires TLS)."""
        _, _, query = (self.DATABASE_URL or "").partition("?")
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        sslmode = params.get("sslmode")
        if sslmode in ("require", "verify-ca", "verify-full", "prefer"):
            return {"ssl": sslmode}
        return {}

    @property
    def allowed_origin(self) -> str:
        return self.ALLOWED_ORIGIN

    @property
    def environment(self) -> str:
        return self.ENVIRONMENT

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY or self.SESSION_SECRET

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """AC-12 (SEC10): Refuse to start in production mode with missing or placeholder secrets."""
        if self.ENVIRONMENT.lower() == "production":
            key = (self.SECRET_KEY or self.SESSION_SECRET or "").strip()
            placeholder_values = {
                "",
                "change-this-in-production-to-a-secure-random-string",
                "insecure-secret-key-change-in-production",
                "placeholder",
            }
            if key in placeholder_values or len(key) < 16:
                raise ValueError(
                    "Production mode requires a strong, non-placeholder secret key (spec SEC10, AC-12)"
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
