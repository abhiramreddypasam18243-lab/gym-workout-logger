"""Nutrition logging and planned vs logged analytics service (spec §6, §5.8, FR-12, AC-82–84)."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.comparison import compare_planned_vs_logged
from app.domain.nutrients import (
    NutrientProfile,
    RecipeIngredientInput,
    calculate_recipe_nutrients,
)
from app.models.nutrition import (
    Food,
    FoodNutrient,
    MealPlan,
    NutritionGoal,
    NutritionLog,
    NutritionLogItem,
    PlannedMeal,
    PlannedMealItem,
    Recipe,
    RecipeIngredient,
)
from app.models.user import UserProfile
from app.schemas.nutrition_log import (
    NutritionAnalyticsResponse,
    NutritionLogCreate,
    NutritionLogItemCreate,
    NutritionLogItemResponse,
    NutritionLogResponse,
    NutritionLogUpdate,
    PlannedVsLoggedDayResponse,
)
from app.services.planner import DISCLAIMER_TEXT


class NutritionLogService:
    """Handles intake logging, item editing/deletion, and planned vs logged comparison."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_timezone(self, user_id: UUID) -> ZoneInfo:
        """Fetch user timezone or fallback to UTC."""
        stmt = select(UserProfile.timezone).where(UserProfile.user_id == user_id)
        tz_str = (await self.db.execute(stmt)).scalar_one_or_none()
        if tz_str:
            try:
                return ZoneInfo(tz_str)
            except Exception:
                pass
        return ZoneInfo("UTC")

    async def create_log(
        self,
        user_id: UUID,
        payload: NutritionLogCreate,
    ) -> NutritionLogResponse:
        """Create a new nutrition intake log with item snapshots (AC-82)."""
        # Determine source type (food or recipe)
        source_type = "food"
        if any(item.recipe_id is not None for item in payload.items):
            source_type = "recipe"

        log = NutritionLog(
            user_id=user_id,
            consumed_at=payload.consumed_at,
            meal_type=payload.meal_type,
            source_type=source_type,
            notes=payload.notes,
        )
        self.db.add(log)
        await self.db.flush()

        log_items = await self._build_log_items(log.id, payload.items)
        for it in log_items:
            self.db.add(it)
        await self.db.commit()

        return await self.get_log_or_404(log.id, user_id)

    async def _build_log_items(
        self,
        log_id: UUID,
        item_inputs: Sequence[NutritionLogItemCreate],
    ) -> list[NutritionLogItem]:
        """Resolve nutrients and create historical snapshots for log items (AC-54, AC-82)."""
        created_items: list[NutritionLogItem] = []

        for item_in in item_inputs:
            snapshot: dict[str, Any] = {}

            if item_in.food_id:
                # Fetch food and nutrients
                f_stmt = (
                    select(Food)
                    .where(Food.id == item_in.food_id)
                    .options(selectinload(Food.nutrients))
                )
                food = (await self.db.execute(f_stmt)).scalars().first()
                if not food:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"food_{item_in.food_id}_not_found",
                    )

                snapshot = {fn.nutrient_code: str(fn.amount_per_100g) for fn in food.nutrients}

                # If logged as serving, convert quantity based on default serving
                actual_qty = item_in.quantity
                unit_str = item_in.unit.lower()
                if unit_str in ("serving", "servings"):
                    serving_g = food.default_serving_g or Decimal("100")
                    actual_qty = item_in.quantity * serving_g
                    unit_str = "g"

                log_item = NutritionLogItem(
                    nutrition_log_id=log_id,
                    food_id=food.id,
                    recipe_id=None,
                    quantity=actual_qty,
                    unit=unit_str,
                    nutrient_snapshot=snapshot,
                )
                created_items.append(log_item)

            elif item_in.recipe_id:
                # Fetch recipe with full ingredients
                r_stmt = (
                    select(Recipe)
                    .where(Recipe.id == item_in.recipe_id)
                    .options(
                        selectinload(Recipe.ingredients)
                        .selectinload(RecipeIngredient.food)
                        .selectinload(Food.nutrients),
                    )
                )
                recipe = (await self.db.execute(r_stmt)).scalars().first()
                if not recipe:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"recipe_{item_in.recipe_id}_not_found",
                    )

                # Compute recipe per-serving nutrients
                ing_inputs: list[RecipeIngredientInput] = []
                for ing in recipe.ingredients:
                    if ing.food:
                        nutr_map = {fn.nutrient_code: fn.amount_per_100g for fn in ing.food.nutrients}
                        profile = NutrientProfile(
                            calories=Decimal(str(nutr_map.get("energy_kcal", 0))),
                            protein_g=Decimal(str(nutr_map.get("protein_g", 0))),
                            carbs_g=Decimal(str(nutr_map.get("carbs_g", 0))),
                            fat_g=Decimal(str(nutr_map.get("fat_g", 0))),
                            fiber_g=Decimal(str(nutr_map.get("fiber_g", 0))),
                        )
                        ing_inputs.append(
                            RecipeIngredientInput(
                                food_nutrients=profile,
                                quantity_g=ing.quantity,
                            )
                        )

                rec_result = calculate_recipe_nutrients(ing_inputs, recipe.servings)
                snapshot = {
                    "energy_kcal": str(rec_result.per_serving.calories),
                    "protein_g": str(rec_result.per_serving.protein_g),
                    "carbs_g": str(rec_result.per_serving.carbs_g),
                    "fat_g": str(rec_result.per_serving.fat_g),
                    "fiber_g": str(rec_result.per_serving.fiber_g),
                    "is_recipe_per_serving": "true",
                }

                log_item = NutritionLogItem(
                    nutrition_log_id=log_id,
                    food_id=None,
                    recipe_id=recipe.id,
                    quantity=item_in.quantity,
                    unit=item_in.unit,
                    nutrient_snapshot=snapshot,
                )
                created_items.append(log_item)

        return created_items

    async def get_log_or_404(self, log_id: UUID, user_id: UUID) -> NutritionLogResponse:
        """Fetch a single log entry or return 404 (SEC4)."""
        stmt = (
            select(NutritionLog)
            .where(NutritionLog.id == log_id, NutritionLog.user_id == user_id)
            .options(
                selectinload(NutritionLog.items).selectinload(NutritionLogItem.food),
                selectinload(NutritionLog.items).selectinload(NutritionLogItem.recipe),
            )
        )
        log = (await self.db.execute(stmt)).scalars().first()
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="nutrition_log_not_found")

        return self._serialize_log(log)

    async def list_logs(
        self,
        user_id: UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[NutritionLogResponse]:
        """List user's logs within date range."""
        stmt = (
            select(NutritionLog)
            .where(NutritionLog.user_id == user_id)
            .options(
                selectinload(NutritionLog.items).selectinload(NutritionLogItem.food),
                selectinload(NutritionLog.items).selectinload(NutritionLogItem.recipe),
            )
            .order_by(NutritionLog.consumed_at.desc())
        )
        logs = (await self.db.execute(stmt)).scalars().all()

        tz = await self.get_user_timezone(user_id)
        filtered_logs: list[NutritionLogResponse] = []
        for l in logs:
            local_day = l.consumed_at.astimezone(tz).date()
            if from_date and local_day < from_date:
                continue
            if to_date and local_day > to_date:
                continue
            filtered_logs.append(self._serialize_log(l))

        return filtered_logs

    async def update_log(
        self,
        user_id: UUID,
        log_id: UUID,
        payload: NutritionLogUpdate,
    ) -> NutritionLogResponse:
        """Update intake log metadata or items with snapshot recomputation (AC-82)."""
        stmt = (
            select(NutritionLog)
            .where(NutritionLog.id == log_id, NutritionLog.user_id == user_id)
            .options(
                selectinload(NutritionLog.items).selectinload(NutritionLogItem.food),
                selectinload(NutritionLog.items).selectinload(NutritionLogItem.recipe),
            )
        )
        log = (await self.db.execute(stmt)).scalars().first()
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="nutrition_log_not_found")

        if payload.consumed_at is not None:
            log.consumed_at = payload.consumed_at
        if payload.meal_type is not None:
            log.meal_type = payload.meal_type
        if payload.notes is not None:
            log.notes = payload.notes

        if payload.items is not None:
            new_items = await self._build_log_items(log.id, payload.items)
            log.items.clear()
            for it in new_items:
                log.items.append(it)

        await self.db.commit()
        return await self.get_log_or_404(log.id, user_id)

    async def delete_log(self, user_id: UUID, log_id: UUID) -> None:
        """Delete an intake log entry (AC-82)."""
        stmt = select(NutritionLog).where(NutritionLog.id == log_id, NutritionLog.user_id == user_id)
        log = (await self.db.execute(stmt)).scalars().first()
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="nutrition_log_not_found")

        await self.db.delete(log)
        await self.db.commit()

    def _serialize_log(self, log: NutritionLog) -> NutritionLogResponse:
        """Calculate nutrients from snapshots and serialize log."""
        items_resp: list[NutritionLogItemResponse] = []
        tot_cal = Decimal("0")
        tot_prot = Decimal("0")
        tot_carbs = Decimal("0")
        tot_fat = Decimal("0")

        for it in log.items:
            cal = Decimal("0")
            prot = Decimal("0")
            carbs = Decimal("0")
            fat = Decimal("0")

            if it.nutrient_snapshot:
                snap = it.nutrient_snapshot
                is_rec = snap.get("is_recipe_per_serving") == "true"
                if is_rec:
                    # Quantity is servings
                    cal = it.quantity * Decimal(str(snap.get("energy_kcal", 0)))
                    prot = it.quantity * Decimal(str(snap.get("protein_g", 0)))
                    carbs = it.quantity * Decimal(str(snap.get("carbs_g", 0)))
                    fat = it.quantity * Decimal(str(snap.get("fat_g", 0)))
                else:
                    # Quantity is grams, snapshot is per 100g
                    factor = it.quantity / Decimal("100")
                    cal = factor * Decimal(str(snap.get("energy_kcal", 0)))
                    prot = factor * Decimal(str(snap.get("protein_g", 0)))
                    carbs = factor * Decimal(str(snap.get("carbs_g", 0)))
                    fat = factor * Decimal(str(snap.get("fat_g", 0)))

            tot_cal += cal
            tot_prot += prot
            tot_carbs += carbs
            tot_fat += fat

            items_resp.append(
                NutritionLogItemResponse(
                    id=it.id,
                    food_id=it.food_id,
                    food_name=it.food.name if it.food else None,
                    recipe_id=it.recipe_id,
                    recipe_title=it.recipe.name if it.recipe else None,
                    quantity=it.quantity,
                    unit=it.unit,
                    nutrient_snapshot=it.nutrient_snapshot,
                    calories=cal,
                    protein_g=prot,
                    carbs_g=carbs,
                    fat_g=fat,
                )
            )

        return NutritionLogResponse(
            id=log.id,
            consumed_at=log.consumed_at,
            meal_type=log.meal_type,
            source_type=log.source_type,
            notes=log.notes,
            items=items_resp,
            total_calories=tot_cal,
            total_protein_g=tot_prot,
            total_carbs_g=tot_carbs,
            total_fat_g=tot_fat,
        )

    async def get_planned_vs_logged_analytics(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> NutritionAnalyticsResponse:
        """Compute planned vs logged comparison across dates in user's timezone (spec §5.8, AC-83, AC-84)."""
        tz = await self.get_user_timezone(user_id)

        # 1. Fetch user meal plans that might overlap
        p_stmt = (
            select(MealPlan)
            .where(
                MealPlan.user_id == user_id,
                MealPlan.start_date <= end_date,
                MealPlan.end_date >= start_date,
            )
            .options(
                selectinload(MealPlan.meals)
                .selectinload(PlannedMeal.items),
            )
        )
        plans = (await self.db.execute(p_stmt)).scalars().all()

        # Map planned day -> (planned_cal, planned_prot)
        planned_by_date: dict[date, tuple[Decimal, Decimal]] = {}
        for p in plans:
            for m in p.meals:
                m_cal = Decimal("0")
                m_prot = Decimal("0")
                for it in m.items:
                    if it.nutrient_snapshot:
                        factor = it.quantity / Decimal("100")
                        m_cal += factor * Decimal(str(it.nutrient_snapshot.get("energy_kcal", 0)))
                        m_prot += factor * Decimal(str(it.nutrient_snapshot.get("protein_g", 0)))

                cur_c, cur_p = planned_by_date.get(m.plan_date, (Decimal("0"), Decimal("0")))
                planned_by_date[m.plan_date] = (cur_c + m_cal, cur_p + m_prot)

        # 2. Fetch active nutrition goals in case plan is absent for some dates
        g_stmt = (
            select(NutritionGoal)
            .where(NutritionGoal.user_id == user_id, NutritionGoal.effective_from <= end_date)
            .order_by(NutritionGoal.effective_from.asc())
        )
        goals = (await self.db.execute(g_stmt)).scalars().all()

        # 3. Fetch all user logs
        l_stmt = (
            select(NutritionLog)
            .where(NutritionLog.user_id == user_id)
            .options(
                selectinload(NutritionLog.items),
            )
        )
        all_logs = (await self.db.execute(l_stmt)).scalars().all()

        # Map logged day in user's timezone -> (logged_cal, logged_prot)
        logged_by_date: dict[date, tuple[Decimal, Decimal]] = defaultdict(lambda: (Decimal("0"), Decimal("0")))
        logged_days_set: set[date] = set()

        for l in all_logs:
            local_day = l.consumed_at.astimezone(tz).date()
            if start_date <= local_day <= end_date:
                logged_days_set.add(local_day)
                l_cal = Decimal("0")
                l_prot = Decimal("0")
                for it in l.items:
                    if it.nutrient_snapshot:
                        snap = it.nutrient_snapshot
                        is_rec = snap.get("is_recipe_per_serving") == "true"
                        if is_rec:
                            l_cal += it.quantity * Decimal(str(snap.get("energy_kcal", 0)))
                            l_prot += it.quantity * Decimal(str(snap.get("protein_g", 0)))
                        else:
                            factor = it.quantity / Decimal("100")
                            l_cal += factor * Decimal(str(snap.get("energy_kcal", 0)))
                            l_prot += factor * Decimal(str(snap.get("protein_g", 0)))

                cur_c, cur_p = logged_by_date[local_day]
                logged_by_date[local_day] = (cur_c + l_cal, cur_p + l_prot)

        # 4. Generate daily comparisons for every date in range
        day_results: list[PlannedVsLoggedDayResponse] = []
        tot_log_cal = Decimal("0")
        tot_log_prot = Decimal("0")

        # Iterate day by day from start_date to end_date
        cur_d = start_date
        from datetime import timedelta
        while cur_d <= end_date:
            is_logged = cur_d in logged_days_set

            # Resolve planned targets for this day
            p_cal = None
            p_prot = None
            if cur_d in planned_by_date:
                p_cal, p_prot = planned_by_date[cur_d]
            else:
                # Check target goal on this date
                active_goal = next((g for g in reversed(goals) if g.effective_from <= cur_d), None)
                if active_goal:
                    if active_goal.calorie_target_kcal:
                        p_cal = Decimal(str(active_goal.calorie_target_kcal))
                    if active_goal.protein_target_g:
                        p_prot = Decimal(str(active_goal.protein_target_g))

            if not is_logged:
                # AC-84: Unlogged days are "not logged" and excluded from averages
                day_results.append(
                    PlannedVsLoggedDayResponse(
                        date=cur_d,
                        is_logged=False,
                        planned_calories=p_cal,
                        logged_calories=None,
                        calories_difference=None,
                        calories_difference_pct=None,
                        planned_protein_g=p_prot,
                        logged_protein_g=None,
                        protein_difference_g=None,
                        protein_difference_pct=None,
                        is_within_range=None,
                        status_label="Not logged",
                    )
                )
            else:
                l_cal, l_prot = logged_by_date[cur_d]
                tot_log_cal += l_cal
                tot_log_prot += l_prot

                if p_cal and p_prot and p_cal > Decimal("0") and p_prot > Decimal("0"):
                    comp = compare_planned_vs_logged(p_cal, p_prot, l_cal, l_prot)
                    day_results.append(
                        PlannedVsLoggedDayResponse(
                            date=cur_d,
                            is_logged=True,
                            planned_calories=p_cal,
                            logged_calories=l_cal,
                            calories_difference=comp.calories_diff,
                            calories_difference_pct=comp.calories_diff_pct,
                            planned_protein_g=p_prot,
                            logged_protein_g=l_prot,
                            protein_difference_g=comp.protein_diff_g,
                            protein_difference_pct=comp.protein_diff_pct,
                            is_within_range=comp.is_within_range,
                            status_label=comp.status_label,
                        )
                    )
                else:
                    day_results.append(
                        PlannedVsLoggedDayResponse(
                            date=cur_d,
                            is_logged=True,
                            planned_calories=p_cal,
                            logged_calories=l_cal,
                            calories_difference=None,
                            calories_difference_pct=None,
                            planned_protein_g=p_prot,
                            logged_protein_g=l_prot,
                            protein_difference_g=None,
                            protein_difference_pct=None,
                            is_within_range=None,
                            status_label="Logged (no targets)",
                        )
                    )

            cur_d += timedelta(days=1)

        logged_count = len(logged_days_set)
        avg_cal = (tot_log_cal / Decimal(str(logged_count))) if logged_count > 0 else None
        avg_prot = (tot_log_prot / Decimal(str(logged_count))) if logged_count > 0 else None

        return NutritionAnalyticsResponse(
            start_date=start_date,
            end_date=end_date,
            days_logged_count=logged_count,
            average_logged_calories=avg_cal,
            average_logged_protein_g=avg_prot,
            days=day_results,
            disclaimer=DISCLAIMER_TEXT,
        )
