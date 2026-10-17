"""Health check endpoint (D5, AC-107)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Liveness and database status check.

    Returns 200 with database status. Used by Docker health checks
    and monitoring.
    """
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {type(e).__name__}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
    }
