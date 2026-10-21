"""Nutrition targets, estimation, preferences, and safety rules router (spec §5.4, §7, S2–S7, AC-17–28)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_nutrition_access, verify_csrf
from app.database import get_db
from app.domain.allergens import EU_ALLERGENS, normalize_allergen
from app.domain.targets import GOAL_FACTORS, calculate_target_estimate
from app.models.nutrition import NutritionGoal
from app.models.user import Session, User, UserCuisinePreference, UserFoodConstraint
from app.schemas.nutrition import (
    NutritionEstimateRequest,
    NutritionEstimateResponse,
    NutritionGoalCreate,
    NutritionGoalResponse,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


@router.post("/goals/estimate", response_model=NutritionEstimateResponse)
async def estimate_nutrition_targets(
    request: Request,
    payload: NutritionEstimateRequest,
    auth: Annotated[tuple[User, Session], Depends(check_nutrition_access)],
    _csrf: Annotated[None, Depends(verify_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Generate transparent, optional target estimate (spec §5.4, S3, S4, S5, AC-18–21).

    Rules:
    - If needs_professional_guidance is on: return 409 manual_targets_required (S3, AC-18).
    - Uses Mifflin-St Jeor equation with transparent inputs, formula and assumptions (S4, AC-19, AC-20).
    - If estimated target < 1500 kcal: return estimate_below_floor, save no target (S5, AC-21).
    - If valid: option to save as active target.
    """
    user, _session = auth
    profile = user.profile

    # Rule S3 (AC-18): Professional guidance blocks automated estimates
    if profile.needs_professional_guidance:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "manual_targets_required",
                "message": (
                    "Because you are working with a healthcare professional, automated estimates are "
                    "disabled. Please enter manual targets as advised by your professional."
                ),
                "requires_professional_guidance": True,
            },
        )

    # Resolve weight (AC-26: opt-in or requested at moment of estimate)
    weight_kg = payload.weight_kg or profile.body_weight_kg
    if not weight_kg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "weight_required",
                "message": "Body weight is required for target estimation. Please provide your weight in kg.",
            },
        )

    # Resolve height
    height_cm = payload.height_cm or profile.height_cm
    if not height_cm:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "height_required",
                "message": "Height is required for target estimation. Please provide your height in cm.",
            },
        )

    # Resolve age from birth_date or payload
    age = payload.age
    if not age and profile.birth_date:
        today = datetime.now(UTC).date()
        bdate = profile.birth_date
        age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))

    if not age:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "age_required",
                "message": "Age or birth date is required for target estimation.",
            },
        )

    sex = payload.sex_for_estimate or profile.sex_for_estimate or "unspecified"
    if sex not in ("male", "female", "unspecified"):
        sex = "unspecified"

    activity_level = payload.activity_level or profile.activity_level or "moderate"
    if activity_level not in ("sedentary", "light", "moderate", "very_active"):
        activity_level = "moderate"

    goal = payload.goal or profile.goal or "build_strength"
    if goal not in GOAL_FACTORS:
        goal = "build_strength"

    # Compute estimate using pure domain logic
    est = calculate_target_estimate(
        weight_kg=Decimal(str(weight_kg)),
        height_cm=Decimal(str(height_cm)),
        age=age,
        sex=sex,
        activity_level=activity_level,
        goal=goal,
        estimate_floor_kcal=Decimal("1500"),
    )

    # S5 & AC-21: Check energy floor (< 1500 kcal)
    if est.is_below_floor:
        return {
            "status": "estimate_below_floor",
            "calories": None,
            "protein_g": None,
            "fat_g": None,
            "carbs_g": None,
            "bmr": str(est.bmr),
            "tdee": str(est.tdee),
            "formula": "Mifflin-St Jeor: 10*weight_kg + 6.25*height_cm - 5*age + s",
            "activity_factor": str(est.assumptions["activity_factor"]),
            "goal_adjustment": str(est.assumptions["goal_factor"]),
            "protein_assumption": "1.6 g/kg body weight",
            "fat_assumption": "25% of calories",
            "assumptions": {
                k: str(v) if isinstance(v, Decimal) else v for k, v in est.assumptions.items()
            },
            "warning": (
                f"Estimated energy ({est.calories} kcal) is below the recommended minimum floor of "
                f"1,500 kcal. Please enter a target manually or consult a registered dietitian or doctor."
            ),
            "requires_professional_guidance": False,
            "disclaimer": (
                "Estimates are informational and not medical advice, and this app is not a substitute "
                "for a registered dietitian or doctor."
            ),
        }

    # S4, AC-19, AC-20: Valid estimate
    # Optionally save as active goal if requested
    if payload.save_as_active:
        today_local = datetime.now(ZoneInfo(profile.timezone or "UTC")).date()
        new_goal = NutritionGoal(
            user_id=user.id,
            effective_from=today_local,
            calorie_target_kcal=est.calories,
            protein_target_g=est.protein_g,
            fat_target_g=est.fat_g,
            carbs_target_g=est.carbs_g,
            rationale="Mifflin-St Jeor automated estimate",
        )
        db.add(new_goal)
        await db.commit()

    return {
        "status": "ok",
        "calories": est.calories,
        "protein_g": est.protein_g,
        "fat_g": est.fat_g,
        "carbs_g": est.carbs_g,
        "bmr": str(est.bmr),
        "tdee": str(est.tdee),
        "formula": "Mifflin-St Jeor: 10*weight_kg + 6.25*height_cm - 5*age + s",
        "activity_factor": str(est.assumptions["activity_factor"]),
        "goal_adjustment": str(est.assumptions["goal_factor"]),
        "protein_assumption": "1.6 g/kg body weight",
        "fat_assumption": "25% of calories",
        "assumptions": {
            k: str(v) if isinstance(v, Decimal) else v for k, v in est.assumptions.items()
        },
        "warning": None,
        "requires_professional_guidance": False,
        "disclaimer": (
            "Estimates are informational and not medical advice, and this app is not a substitute "
            "for a registered dietitian or doctor."
        ),
    }


@router.post("/goals", status_code=status.HTTP_201_CREATED, response_model=NutritionGoalResponse)
async def create_nutrition_goal(
    payload: NutritionGoalCreate,
    auth: Annotated[tuple[User, Session], Depends(check_nutrition_access)],
    _csrf: Annotated[None, Depends(verify_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Save a new versioned nutrition target (spec §5.4, S5, AC-22, AC-23).

    Rules:
    - Creating/changing a target creates a new nutrition_goals row (AC-23).
    - If calorie_target_kcal < 1500: saves with warning 'below_recommended_minimum' (AC-22).
    - Returns target with disclaimer (AC-28).
    """
    user, _session = auth
    profile = user.profile

    today_local = datetime.now(ZoneInfo(profile.timezone or "UTC")).date()
    eff_from = payload.effective_from or today_local

    # Warning for manual target below 1500 kcal (S5, AC-22)
    warning = None
    if payload.calorie_target_kcal and payload.calorie_target_kcal < 1500:
        warning = "below_recommended_minimum"

    new_goal = NutritionGoal(
        user_id=user.id,
        effective_from=eff_from,
        calorie_target_kcal=payload.calorie_target_kcal,
        protein_target_g=payload.protein_target_g,
        carbs_target_g=payload.carbs_target_g,
        fat_target_g=payload.fat_target_g,
        rationale=payload.rationale,
    )
    db.add(new_goal)
    await db.commit()
    await db.refresh(new_goal)

    return {
        "id": str(new_goal.id),
        "effective_from": new_goal.effective_from.isoformat(),
        "calorie_target_kcal": new_goal.calorie_target_kcal,
        "protein_target_g": new_goal.protein_target_g,
        "carbs_target_g": new_goal.carbs_target_g,
        "fat_target_g": new_goal.fat_target_g,
        "rationale": new_goal.rationale,
        "warning": warning,
        "created_at": new_goal.created_at,
        "disclaimer": (
            "Estimates are informational and not medical advice, and this app is not a substitute "
            "for a registered dietitian or doctor."
        ),
    }


@router.get("/goals", response_model=NutritionGoalResponse | None)
async def get_active_nutrition_goal(
    auth: Annotated[tuple[User, Session], Depends(check_nutrition_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    on_date: date | None = Query(None, description="Query date (defaults to today in user timezone)"),
) -> dict | None:
    """Retrieve active nutrition target on a given date (spec §5.4, AC-23).

    Returns the latest nutrition_goals row with effective_from on or before target date.
    """
    user, _session = auth
    profile = user.profile

    target_date = on_date or datetime.now(ZoneInfo(profile.timezone or "UTC")).date()

    stmt = (
        select(NutritionGoal)
        .where(
            NutritionGoal.user_id == user.id,
            NutritionGoal.effective_from <= target_date,
        )
        .order_by(NutritionGoal.effective_from.desc(), NutritionGoal.created_at.desc())
        .limit(1)
    )

    result = await db.execute(stmt)
    goal = result.scalar_one_or_none()

    if not goal:
        return None

    warning = None
    if goal.calorie_target_kcal and goal.calorie_target_kcal < 1500:
        warning = "below_recommended_minimum"

    return {
        "id": str(goal.id),
        "effective_from": goal.effective_from.isoformat(),
        "calorie_target_kcal": goal.calorie_target_kcal,
        "protein_target_g": goal.protein_target_g,
        "carbs_target_g": goal.carbs_target_g,
        "fat_target_g": goal.fat_target_g,
        "rationale": goal.rationale,
        "warning": warning,
        "created_at": goal.created_at,
        "disclaimer": (
            "Estimates are informational and not medical advice, and this app is not a substitute "
            "for a registered dietitian or doctor."
        ),
    }


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_nutrition_preferences(
    auth: Annotated[tuple[User, Session], Depends(check_nutrition_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get user dietary constraints, allergies, and cuisine preferences (spec §6, FR-06)."""
    user, _session = auth

    # Load constraints
    stmt_c = select(UserFoodConstraint).where(UserFoodConstraint.user_id == user.id)
    constraints = (await db.execute(stmt_c)).scalars().all()

    allergies = [c.constraint_value for c in constraints if c.constraint_type == "allergy"]
    diet_tags = [c.constraint_value for c in constraints if c.constraint_type == "diet_tag"]
    excluded = [c.constraint_value for c in constraints if c.constraint_type == "excluded_ingredient"]

    # Load cuisine preferences
    stmt_cp = select(UserCuisinePreference).where(UserCuisinePreference.user_id == user.id)
    cuisines = (await db.execute(stmt_cp)).scalars().all()
    cuisine_prefs = {c.cuisine_code: c.preference_level for c in cuisines}

    return {
        "allergies": allergies,
        "diet_tags": diet_tags,
        "excluded_ingredients": excluded,
        "cuisine_preferences": cuisine_prefs,
        "max_minutes_per_meal": 60,
        "daily_budget": None,
        "exclude_unverified_allergens": True,
        "disclaimer": (
            "Estimates are informational and not medical advice, and this app is not a substitute "
            "for a registered dietitian or doctor."
        ),
    }


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_user_nutrition_preferences(
    payload: UserPreferencesUpdate,
    auth: Annotated[tuple[User, Session], Depends(check_nutrition_access)],
    _csrf: Annotated[None, Depends(verify_csrf)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update dietary constraints, allergies, and cuisine preferences (spec §6, FR-06, S9)."""
    user, _session = auth

    if payload.allergies is not None:
        # The planner's allergy filter is an exact match on catalogue codes (S9, D-31)
        allergy_codes: list[str] = []
        for raw in payload.allergies:
            code = normalize_allergen(raw)
            if code is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "unknown_allergen",
                        "message": f"'{raw}' is not one of the 14 EU allergens",
                        "allowed": list(EU_ALLERGENS),
                    },
                )
            if code not in allergy_codes:
                allergy_codes.append(code)
        await db.execute(
            delete(UserFoodConstraint).where(
                UserFoodConstraint.user_id == user.id,
                UserFoodConstraint.constraint_type == "allergy",
            )
        )
        for code in allergy_codes:
            db.add(
                UserFoodConstraint(
                    user_id=user.id,
                    constraint_type="allergy",
                    constraint_value=code,
                    is_hard_constraint=True,
                )
            )

    if payload.diet_tags is not None:
        await db.execute(
            delete(UserFoodConstraint).where(
                UserFoodConstraint.user_id == user.id,
                UserFoodConstraint.constraint_type == "diet_tag",
            )
        )
        for dt in payload.diet_tags:
            db.add(
                UserFoodConstraint(
                    user_id=user.id,
                    constraint_type="diet_tag",
                    constraint_value=dt.lower().strip(),
                    is_hard_constraint=True,
                )
            )

    if payload.excluded_ingredients is not None:
        await db.execute(
            delete(UserFoodConstraint).where(
                UserFoodConstraint.user_id == user.id,
                UserFoodConstraint.constraint_type == "excluded_ingredient",
            )
        )
        for ex in payload.excluded_ingredients:
            db.add(
                UserFoodConstraint(
                    user_id=user.id,
                    constraint_type="excluded_ingredient",
                    constraint_value=ex.lower().strip(),
                    is_hard_constraint=True,
                )
            )

    if payload.cuisine_preferences is not None:
        await db.execute(
            delete(UserCuisinePreference).where(UserCuisinePreference.user_id == user.id)
        )
        for code, level in payload.cuisine_preferences.items():
            db.add(
                UserCuisinePreference(
                    user_id=user.id,
                    cuisine_code=code.lower().strip(),
                    preference_level=level,
                )
            )

    await db.commit()

    return await get_user_nutrition_preferences(auth, db)
