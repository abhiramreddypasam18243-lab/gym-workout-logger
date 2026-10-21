"""User profile and wellbeing settings router (spec §6, §7, S2, S3, S7, AC-15, AC-17)."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_session, verify_csrf
from app.database import get_db
from app.models.user import Session, User
from app.schemas.profile import ProfileUpdateRequest

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
async def get_profile(
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
) -> dict[str, Any]:
    """Get current user's profile and settings."""
    user, _session = auth
    p = user.profile
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "profile_not_found", "message": "Profile not found"},
        )

    return {
        "user_id": str(p.user_id),
        "display_name": p.display_name,
        "birth_date": str(p.birth_date) if p.birth_date else None,
        "height_cm": str(p.height_cm) if p.height_cm else None,
        "body_weight_kg": str(p.body_weight_kg) if p.body_weight_kg else None,
        "timezone": p.timezone,
        "units": p.units,
        "sex_for_estimate": p.sex_for_estimate,
        "adult_confirmed_at": p.adult_confirmed_at.isoformat() if p.adult_confirmed_at else None,
        "needs_professional_guidance": p.needs_professional_guidance,
        "calories_hidden": p.calories_hidden,
        "nutrition_paused": p.nutrition_paused,
        "track_body_weight": p.track_body_weight,
        "weekly_session_target": p.weekly_session_target,
        "currency_code": p.currency_code,
        "goal": p.goal,
        "activity_level": p.activity_level,
    }


@router.patch("")
async def update_profile(
    payload: ProfileUpdateRequest,
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    _csrf: Annotated[None, Depends(verify_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Update profile with validation (spec FR-01, AC-15)."""
    user, _session = auth
    p = user.profile
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "profile_not_found", "message": "Profile not found"},
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(p, field, val)

    p.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(p)

    return {
        "user_id": str(p.user_id),
        "display_name": p.display_name,
        "birth_date": str(p.birth_date) if p.birth_date else None,
        "height_cm": str(p.height_cm) if p.height_cm else None,
        "body_weight_kg": str(p.body_weight_kg) if p.body_weight_kg else None,
        "timezone": p.timezone,
        "units": p.units,
        "sex_for_estimate": p.sex_for_estimate,
        "adult_confirmed_at": p.adult_confirmed_at.isoformat() if p.adult_confirmed_at else None,
        "needs_professional_guidance": p.needs_professional_guidance,
        "calories_hidden": p.calories_hidden,
        "nutrition_paused": p.nutrition_paused,
        "track_body_weight": p.track_body_weight,
        "weekly_session_target": p.weekly_session_target,
        "currency_code": p.currency_code,
        "goal": p.goal,
        "activity_level": p.activity_level,
    }


@router.post("/confirm-adult")
async def confirm_adult(
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    _csrf: Annotated[None, Depends(verify_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Record confirmation that the user is 18 or older (spec S2, AC-17)."""
    user, _session = auth
    p = user.profile
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "profile_not_found", "message": "Profile not found"},
        )

    now = datetime.now(UTC)
    p.adult_confirmed_at = now
    await db.commit()

    return {"adult_confirmed_at": now.isoformat()}
