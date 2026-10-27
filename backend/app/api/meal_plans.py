"""Meal plans router (spec §7, FR-08, AC-56–72)."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import check_nutrition_access, get_db, verify_csrf
from app.domain.scoring import DEFAULT_WEIGHTS
from app.models.nutrition import MealPlan, PlannedMeal, PlannedMealItem
from app.models.user import User
from app.schemas.meal_plan import (
    DayNutrientTotal,
    ExplanationBlock,
    GroceryListResponse,
    InfeasibleExplanationResponse,
    MealEditRequest,
    MealNutrientSummary,
    MealPlanGenerateRequest,
    MealPlanResponse,
    PlannedMealItemResponse,
    PlannedMealResponse,
    SubstitutionAcceptRequest,
    SubstitutionOptionResponse,
    SubstitutionSuggestRequest,
)
from app.services.planner import DISCLAIMER_TEXT, DietPlannerService
from app.services.substitutions import SubstitutionService

router = APIRouter(prefix="/api/meal-plans", tags=["meal-plans"])


@router.post(
    "/generate",
    response_model=MealPlanResponse | InfeasibleExplanationResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_meal_plan(
    payload: MealPlanGenerateRequest,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> MealPlanResponse | InfeasibleExplanationResponse:
    """Generate a deterministic 7-day meal plan or return an infeasible explanation (AC-56–72)."""
    current_user, _ = auth
    service = DietPlannerService(db)
    return await service.generate_plan(current_user.id, payload)


@router.get("", response_model=list[dict[str, Any]])
async def list_meal_plans(
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List meal plans for authenticated user."""
    current_user, _ = auth
    stmt = (
        select(MealPlan)
        .where(MealPlan.user_id == current_user.id)
        .order_by(MealPlan.start_date.desc(), MealPlan.created_at.desc())
    )
    plans = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "start_date": p.start_date,
            "end_date": p.end_date,
            "status": p.status,
            "generation_version": p.generation_version,
            "created_at": p.created_at,
        }
        for p in plans
    ]


@router.get("/{plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(
    plan_id: UUID,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    db: AsyncSession = Depends(get_db),
) -> MealPlanResponse:
    """Get full meal plan details by ID."""
    current_user, _ = auth
    stmt = (
        select(MealPlan)
        .where(MealPlan.id == plan_id, MealPlan.user_id == current_user.id)
        .options(
            selectinload(MealPlan.meals)
            .selectinload(PlannedMeal.items)
            .selectinload(PlannedMealItem.food),
            selectinload(MealPlan.meals)
            .selectinload(PlannedMeal.recipe),
        )
    )
    plan = (await db.execute(stmt)).scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meal_plan_not_found")

    response_meals: list[PlannedMealResponse] = []
    meals_by_date: dict[Any, list[PlannedMealResponse]] = defaultdict(list)

    for m in plan.meals:
        # Sum items to compute meal nutrients
        cal = Decimal("0")
        prot = Decimal("0")
        carbs = Decimal("0")
        fat = Decimal("0")
        fib = Decimal("0")

        items_resp: list[PlannedMealItemResponse] = []
        for it in m.items:
            items_resp.append(
                PlannedMealItemResponse(
                    id=it.id,
                    food_id=it.food_id,
                    ingredient_name=it.ingredient_name
                    or (it.food.name if it.food else "Ingredient"),
                    quantity=it.quantity,
                    unit=it.unit,
                    nutrient_snapshot=it.nutrient_snapshot,
                )
            )
            if it.nutrient_snapshot:
                factor = it.quantity / Decimal("100")
                cal += factor * Decimal(str(it.nutrient_snapshot.get("energy_kcal", 0)))
                prot += factor * Decimal(str(it.nutrient_snapshot.get("protein_g", 0)))
                carbs += factor * Decimal(str(it.nutrient_snapshot.get("carbs_g", 0)))
                fat += factor * Decimal(str(it.nutrient_snapshot.get("fat_g", 0)))
                fib += factor * Decimal(str(it.nutrient_snapshot.get("fiber_g", 0)))

        meal_nutrients = MealNutrientSummary(
            calories=cal,
            protein_g=prot,
            carbs_g=carbs,
            fat_g=fat,
            fiber_g=fib,
        )

        cost_minor = None
        if m.recipe and m.recipe.cost_minor_per_serving is not None:
            cost_minor = int(Decimal(m.recipe.cost_minor_per_serving) * m.servings)

        meal_resp = PlannedMealResponse(
            id=m.id,
            plan_date=m.plan_date,
            meal_type=m.meal_type,
            recipe_id=m.recipe_id,
            title=m.title,
            servings=m.servings,
            sort_order=m.sort_order,
            cuisine_code=m.recipe.cuisine_code if m.recipe else None,
            total_minutes=(m.recipe.prep_minutes + m.recipe.cook_minutes) if m.recipe else 0,
            cost_minor=cost_minor,
            nutrients=meal_nutrients,
            items=items_resp,
        )
        response_meals.append(meal_resp)
        meals_by_date[m.plan_date].append(meal_resp)

    # Compute day totals
    response_days: list[DayNutrientTotal] = []
    target_kcal = None
    target_protein = None
    if plan.target_snapshot and "targets" in plan.target_snapshot:
        t = plan.target_snapshot["targets"]
        target_kcal = t.get("calorie_target_kcal")
        target_protein = t.get("protein_target_g")

    for p_date in sorted(meals_by_date.keys()):
        day_m_list = meals_by_date[p_date]
        d_cal = sum((m.nutrients.calories for m in day_m_list), Decimal("0"))
        d_prot = sum((m.nutrients.protein_g for m in day_m_list), Decimal("0"))
        d_carbs = sum((m.nutrients.carbs_g for m in day_m_list), Decimal("0"))
        d_fat = sum((m.nutrients.fat_g for m in day_m_list), Decimal("0"))
        d_fib = sum((m.nutrients.fiber_g for m in day_m_list), Decimal("0"))

        deviations = []
        is_within = True
        if target_kcal:
            diff_pct = (d_cal - Decimal(target_kcal)) / Decimal(target_kcal)
            if abs(diff_pct) > Decimal("0.10"):
                is_within = False
                deviations.append(
                    {
                        "warning": "target_deviation",
                        "day": str(p_date),
                        "metric": "calories",
                        "target": target_kcal,
                        "actual": int(round(d_cal)),
                        "difference_pct": round(float(diff_pct * 100), 1),
                    }
                )
        if target_protein and d_prot < Decimal("0.90") * Decimal(target_protein):
            is_within = False
            diff_prot_pct = (d_prot - Decimal(target_protein)) / Decimal(target_protein)
            deviations.append(
                {
                    "warning": "target_deviation",
                    "day": str(p_date),
                    "metric": "protein",
                    "target": target_protein,
                    "actual": int(round(d_prot)),
                    "difference_pct": round(float(diff_prot_pct * 100), 1),
                }
            )

        response_days.append(
            DayNutrientTotal(
                plan_date=p_date,
                calories=d_cal,
                protein_g=d_prot,
                carbs_g=d_carbs,
                fat_g=d_fat,
                fiber_g=d_fib,
                calorie_target=target_kcal,
                protein_target=target_protein,
                is_within_range=is_within,
                deviations=deviations,
            )
        )

    stored_explanation = (plan.target_snapshot or {}).get("explanation")
    if stored_explanation:
        explanation = ExplanationBlock.model_validate(stored_explanation)
    else:
        # Plans generated before the explanation was stored with the plan
        explanation = ExplanationBlock(
            constraints_applied=[],
            scoring_weights={k: str(v) for k, v in DEFAULT_WEIGHTS.items()},
            generation_version=plan.generation_version,
            catalog_version="1.0",
            share_approximate_nutrients=0.0,
        )

    return MealPlanResponse(
        id=plan.id,
        name=plan.name,
        start_date=plan.start_date,
        end_date=plan.end_date,
        status=plan.status,
        generation_version=plan.generation_version,
        target_snapshot=plan.target_snapshot,
        meals=response_meals,
        days=response_days,
        # Same notices as at generation: day deviations from the current totals, plus the
        # plan-level notices stored with it (AC-61, AC-67)
        warnings=[d for day in response_days for d in day.deviations]
        + list((plan.target_snapshot or {}).get("notices", [])),
        explanation=explanation,
        disclaimer=DISCLAIMER_TEXT,
    )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan(
    plan_id: UUID,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a meal plan (AC-34, SEC4)."""
    current_user, _ = auth
    stmt = select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == current_user.id)
    plan = (await db.execute(stmt)).scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meal_plan_not_found")

    await db.delete(plan)
    await db.commit()


@router.post("/{plan_id}/substitutions/suggest", response_model=list[SubstitutionOptionResponse])
async def suggest_substitutions(
    plan_id: UUID,
    payload: SubstitutionSuggestRequest,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> list[SubstitutionOptionResponse]:
    """Suggest up to 5 valid replacement recipes scored against slot target (AC-73)."""
    current_user, _ = auth
    service = SubstitutionService(db)
    return await service.suggest_substitutions(current_user.id, plan_id, payload.meal_id)


@router.post("/{plan_id}/substitutions/accept", response_model=MealPlanResponse)
async def accept_substitution(
    plan_id: UUID,
    payload: SubstitutionAcceptRequest,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> MealPlanResponse:
    """Accept substitution: updates meal, day totals, grocery list, and sets status to edited (AC-74)."""
    current_user, _ = auth
    service = SubstitutionService(db)
    await service.accept_substitution(current_user.id, plan_id, payload)
    return await get_meal_plan(plan_id, auth, db)


@router.patch("/{plan_id}/meals/{meal_id}", response_model=MealPlanResponse)
async def edit_planned_meal(
    plan_id: UUID,
    meal_id: UUID,
    payload: MealEditRequest,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> MealPlanResponse:
    """Edit meal servings or recipe with hard safety validation (AC-75, AC-76)."""
    current_user, _ = auth
    service = SubstitutionService(db)
    await service.edit_meal(current_user.id, plan_id, meal_id, payload)
    return await get_meal_plan(plan_id, auth, db)


@router.get("/{plan_id}/grocery-list", response_model=GroceryListResponse)
async def get_plan_grocery_list(
    plan_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    db: AsyncSession = Depends(get_db),
) -> GroceryListResponse:
    """Generate unit-aware grocery list for chosen days with food categorization (AC-77–81)."""
    current_user, _ = auth
    service = SubstitutionService(db)
    return await service.get_grocery_list(current_user.id, plan_id, from_date, to_date)
