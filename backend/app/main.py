"""FastAPI application entry point with security middleware and routers (spec §7, §10, SEC8, SEC9)."""

from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.catalogue import router as catalogue_router
from app.api.dashboard import router as dashboard_router
from app.api.data_controls import router as data_controls_router
from app.api.health import router as health_router
from app.api.meal_plans import router as meal_plans_router
from app.api.nutrition import router as nutrition_router
from app.api.nutrition_logs import router as nutrition_logs_router
from app.api.profile import router as profile_router
from app.api.workouts import router as workout_router
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
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'"
    )

    return response


# CORS (SEC9, AC-11) — configured origins
allowed_origins = list({settings.allowed_origin, "http://localhost:5173", "http://localhost:8080", "http://127.0.0.1:5173"})
if settings.allowed_origin == "*" or "*" in settings.allowed_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(catalogue_router)
app.include_router(workout_router)
app.include_router(analytics_router)
app.include_router(nutrition_router)
app.include_router(meal_plans_router)
app.include_router(nutrition_logs_router)
app.include_router(dashboard_router)
app.include_router(data_controls_router)

# Static frontend assets and SPA fallback for production deployment
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists() and (static_dir / "index.html").exists():
    if (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"error": "Not Found"})
        target = static_dir / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(static_dir / "index.html")

