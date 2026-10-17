"""FastAPI application entry point with security middleware and routers (spec §7, §10, SEC8, SEC9)."""

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.profile import router as profile_router
from app.config import settings

app = FastAPI(
    title="Gym Workout Logger & Diet Planner",
    version="0.1.0",
    docs_url="/api/docs" if settings.environment == "development" else None,
    redoc_url="/api/redoc" if settings.environment == "development" else None,
)

# 1 MB body limit in bytes (spec SEC8, AC-13)
MAX_BODY_BYTES = 1024 * 1024


@app.middleware("http")
async def security_and_limits_middleware(request: Request, call_next):
    # 1. Body size limit check (AC-13)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": {"code": "body_too_large", "message": "Request body exceeds 1 MB limit"}
            },
        )

    response: Response = await call_next(request)

    # 2. Security headers (spec SEC9, AC-11)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
    )

    return response


# CORS (SEC9, AC-11) — strictly limited to configured origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(profile_router)
