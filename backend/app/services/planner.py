"""Deterministic 7-day meal plan generator service (spec §5.5, FR-08, AC-56–72).

Implements hard safety filter pipeline (allergens S9, diet tags, exclusions),
multi-factor scoring formula (AC-63), discrete serving size selector (AC-64),
tie-breaking by recipe ID ascending (AC-65), repetition limits (AC-66),
infeasibility explanations (AC-62, AC-72), target deviation warnings (AC-67),
target snapshot preservation (AC-68), and transactional persistence (AC-71).
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.allergens import normalize_allergen
from app.domain.nutrients import (
    NutrientProfile,
    RecipeIngredientInput,
    calculate_recipe_nutrients,
)
from app.domain.scoring import (
    DEFAULT_WEIGHTS,
    affordable_serving_sizes,
    calculate_candidate_score,
    calculate_target_fit,
    select_best_serving_size,
)
from app.models.nutrition import (
    Food,
    MealPlan,
    NutritionGoal,
    PlannedMeal,
    PlannedMealItem,
    Recipe,
    RecipeIngredient,
)
from app.models.user import UserCuisinePreference, UserFoodConstraint
from app.schemas.meal_plan import (
    DayNutrientTotal,
    ExplanationBlock,
    FilterRemovedCount,
    InfeasibleExplanationResponse,
    MealNutrientSummary,
    MealPlanGenerateRequest,
    MealPlanResponse,
    PlannedMealItemResponse,
    PlannedMealResponse,
)

DEFAULT_SLOT_SHARES: dict[str, Decimal] = {
    "breakfast": Decimal("0.25"),
    "lunch": Decimal("0.30"),
    "dinner": Decimal("0.30"),
    "snack": Decimal("0.15"),
}

DISCLAIMER_TEXT = (
    "This meal plan is generated for educational and general planning purposes and "
    "does not constitute clinical nutrition or medical dietary advice."
)


class PreparedRecipe:
    """Precomputed recipe metadata for fast candidate evaluation."""

    def __init__(self, recipe: Recipe):
        self.recipe = recipe
        self.id = recipe.id
        self.name = recipe.name
        self.cuisine_code = recipe.cuisine_code
        self.total_minutes = recipe.prep_minutes + recipe.cook_minutes
        self.servings = recipe.servings
        self.cost_minor_per_serving = recipe.cost_minor_per_serving
        self.cost_currency = recipe.cost_currency

        # Meal slots and diet tags
        self.meal_types = {mt.meal_type.lower() for mt in recipe.meal_types}
        self.diet_tags = {dt.diet_tag.lower() for dt in recipe.diet_tags}

        # Collect allergens and calculate nutrients
        self.allergens: set[str] = set()
        self.has_incomplete_allergens = False
        self.ingredient_search_tokens: list[str] = []

        domain_inputs: list[RecipeIngredientInput] = []
        self.ingredient_snapshots: list[dict[str, Any]] = []

        for ing in recipe.ingredients:
            self.ingredient_search_tokens.append(ing.ingredient_name.lower())
            if ing.food:
                self.ingredient_search_tokens.append(ing.food.name.lower())
                if not ing.food.allergens_verified:
                    self.has_incomplete_allergens = True
                for fa in ing.food.allergens:
                    self.allergens.add(fa.allergen_code.lower())

                # Per-100g nutrients
                fn_map = {fn.nutrient_code: fn.amount_per_100g for fn in ing.food.nutrients}
                profile = NutrientProfile(
                    calories=fn_map.get("energy_kcal", Decimal("0")),
                    protein_g=fn_map.get("protein_g", Decimal("0")),
                    carbs_g=fn_map.get("carbs_g", Decimal("0")),
                    fat_g=fn_map.get("fat_g", Decimal("0")),
                    fiber_g=fn_map.get("fiber_g", Decimal("0")),
                )
                domain_inputs.append(
                    RecipeIngredientInput(
                        food_nutrients=profile,
                        quantity_g=ing.quantity,
                        edible_weight_g=ing.edible_weight_g,
                    )
                )
                self.ingredient_snapshots.append(
                    {
                        "food_id": ing.food_id,
                        "ingredient_name": ing.ingredient_name,
                        "unit": ing.unit,
                        "quantity_base": ing.quantity,
                        "nutrients_per_100g": {k: str(v) for k, v in fn_map.items()},
                        "approximate": bool(ing.food.approximate),
                    }
                )
            else:
                # Text-only ingredient (AC-52)
                self.has_incomplete_allergens = True
                self.ingredient_snapshots.append(
                    {
                        "food_id": None,
                        "ingredient_name": ing.ingredient_name,
                        "unit": ing.unit,
                        "quantity_base": ing.quantity,
                        "nutrients_per_100g": {},
                        "approximate": False,
                    }
                )

        if domain_inputs and recipe.servings > Decimal("0"):
            calc = calculate_recipe_nutrients(domain_inputs, recipe.servings)
            self.per_serving_nutrients = calc.per_serving
        else:
            self.per_serving_nutrients = NutrientProfile(
                calories=Decimal("0"),
                protein_g=Decimal("0"),
                carbs_g=Decimal("0"),
                fat_g=Decimal("0"),
            )


class DietPlannerService:
    """Orchestrates deterministic diet plan generation with safety guardrails."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_plan(
        self,
        user_id: UUID,
        payload: MealPlanGenerateRequest,
    ) -> MealPlanResponse | InfeasibleExplanationResponse:
        """Generate a 7-day plan or return an infeasible explanation (AC-56–72)."""
        # 1. Fetch active nutrition targets on start_date (AC-69)
        goal_stmt = (
            select(NutritionGoal)
            .where(
                NutritionGoal.user_id == user_id,
                NutritionGoal.effective_from <= payload.start_date,
            )
            .order_by(NutritionGoal.effective_from.desc(), NutritionGoal.created_at.desc())
        )
        active_goal = (await self.db.execute(goal_stmt)).scalars().first()
        if not active_goal:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="targets_required",
            )

        # 2. Fetch user food constraints and cuisine preferences (AC-57, AC-59, AC-61)
        constraints_stmt = select(UserFoodConstraint).where(UserFoodConstraint.user_id == user_id)
        user_constraints = (await self.db.execute(constraints_stmt)).scalars().all()

        user_allergies = {
            normalize_allergen(c.constraint_value) or c.constraint_value.lower()
            for c in user_constraints
            if c.constraint_type == "allergy"
        }
        user_diet_tags = {
            c.constraint_value.lower() for c in user_constraints if c.constraint_type == "diet_tag"
        }
        user_excluded = {
            c.constraint_value.lower()
            for c in user_constraints
            if c.constraint_type == "excluded_ingredient"
        }

        cuisines_stmt = select(UserCuisinePreference).where(
            UserCuisinePreference.user_id == user_id
        )
        user_cuisines = (await self.db.execute(cuisines_stmt)).scalars().all()
        cuisine_prefs = {c.cuisine_code.lower(): c.preference_level.lower() for c in user_cuisines}

        # 3. Fetch and prepare candidate recipes
        recipes_stmt = (
            select(Recipe)
            .where(or_(Recipe.owner_user_id.is_(None), Recipe.owner_user_id == user_id))
            .options(
                selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food)
                .selectinload(Food.nutrients),
                selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food)
                .selectinload(Food.allergens),
                selectinload(Recipe.diet_tags),
                selectinload(Recipe.meal_types),
            )
        )
        db_recipes = (await self.db.execute(recipes_stmt)).scalars().all()

        # Eagerly ensure food, nutrients, and allergens on ingredients are loaded
        prep_recipes: list[PreparedRecipe] = []
        for r in db_recipes:
            prep_recipes.append(PreparedRecipe(r))

        # 4. Configure slot shares
        total_share_weight = sum(
            DEFAULT_SLOT_SHARES.get(slot, Decimal("0.25")) for slot in payload.meal_slots
        )
        slot_shares: dict[str, Decimal] = {
            slot: (DEFAULT_SLOT_SHARES.get(slot, Decimal("0.25")) / total_share_weight)
            for slot in payload.meal_slots
        }

        # Track usage across plan for repetition constraints and scoring
        recipe_plan_count: dict[UUID, int] = defaultdict(int)
        previous_day_slot_recipe: dict[str, UUID | None] = {s: None for s in payload.meal_slots}

        planned_days_data: list[dict[str, Any]] = []
        planned_meals_records: list[dict[str, Any]] = []
        constraints_applied_summary: dict[str, int] = defaultdict(int)
        warnings: list[dict[str, Any]] = []

        preferred_cuisines_count = 0
        total_planned_meals_count = 0
        used_avoid_cuisine = False

        # 5. Day-by-day, slot-by-slot generation (AC-56, AC-62–66)
        for day_idx in range(payload.days):
            current_date = payload.start_date + timedelta(days=day_idx)
            day_slot_recipes: dict[str, UUID] = {}
            day_meals: list[dict[str, Any]] = []

            for slot_order, slot in enumerate(payload.meal_slots):
                slot_share = slot_shares[slot]
                slot_kcal = (
                    Decimal(str(active_goal.calorie_target_kcal)) * slot_share
                    if active_goal.calorie_target_kcal
                    else None
                )
                slot_protein = (
                    Decimal(str(active_goal.protein_target_g)) * slot_share
                    if active_goal.protein_target_g
                    else None
                )
                slot_budget = (
                    (Decimal(str(payload.daily_budget_minor)) * slot_share)
                    if payload.daily_budget_minor is not None
                    else None
                )

                # Hard filter pipeline with per-filter removal tracking (AC-62)
                candidates = list(prep_recipes)
                slot_filters_removed: list[FilterRemovedCount] = []

                # Filter 1: Allergens (Rule S9, AC-57)
                for allergen in sorted(user_allergies):
                    surviving = []
                    removed = 0
                    for cand in candidates:
                        if allergen in cand.allergens:
                            removed += 1
                        else:
                            surviving.append(cand)
                    candidates = surviving
                    slot_filters_removed.append(
                        FilterRemovedCount(filter=f"allergy:{allergen}", removed=removed)
                    )
                    constraints_applied_summary[f"allergy:{allergen}"] += removed

                # Filter 2: Unverified allergens if any allergy set (AC-58)
                if user_allergies:
                    surviving = []
                    removed = 0
                    for cand in candidates:
                        if cand.has_incomplete_allergens:
                            removed += 1
                        else:
                            surviving.append(cand)
                    candidates = surviving
                    slot_filters_removed.append(
                        FilterRemovedCount(filter="unverified_allergens", removed=removed)
                    )
                    constraints_applied_summary["unverified_allergens"] += removed

                # Filter 3: Diet tags (AC-59)
                for diet_tag in sorted(user_diet_tags):
                    surviving = []
                    removed = 0
                    for cand in candidates:
                        if diet_tag not in cand.diet_tags:
                            removed += 1
                        else:
                            surviving.append(cand)
                    candidates = surviving
                    slot_filters_removed.append(
                        FilterRemovedCount(filter=f"diet:{diet_tag}", removed=removed)
                    )
                    constraints_applied_summary[f"diet:{diet_tag}"] += removed

                # Filter 4: Excluded ingredients (AC-59)
                for ex_item in sorted(user_excluded):
                    surviving = []
                    removed = 0
                    for cand in candidates:
                        if any(ex_item in token for token in cand.ingredient_search_tokens):
                            removed += 1
                        else:
                            surviving.append(cand)
                    candidates = surviving
                    slot_filters_removed.append(
                        FilterRemovedCount(filter=f"excluded:{ex_item}", removed=removed)
                    )
                    constraints_applied_summary[f"excluded:{ex_item}"] += removed

                # Filter 5: Meal slot compatibility
                surviving = []
                removed = 0
                for cand in candidates:
                    if slot.lower() not in cand.meal_types:
                        removed += 1
                    else:
                        surviving.append(cand)
                candidates = surviving
                slot_filters_removed.append(
                    FilterRemovedCount(filter=f"meal_type:{slot}", removed=removed)
                )
                constraints_applied_summary[f"meal_type:{slot}"] += removed

                # Filter 6: User time cap (AC-60)
                if payload.max_minutes is not None:
                    surviving = []
                    removed = 0
                    for cand in candidates:
                        if cand.total_minutes > payload.max_minutes:
                            removed += 1
                        else:
                            surviving.append(cand)
                    candidates = surviving
                    slot_filters_removed.append(
                        FilterRemovedCount(
                            filter=f"max_minutes:{payload.max_minutes}", removed=removed
                        )
                    )
                    constraints_applied_summary[f"max_minutes:{payload.max_minutes}"] += removed

                # Filter 7: Daily budget cap (AC-60)
                if slot_budget is not None:
                    surviving = []
                    removed = 0
                    for cand in candidates:
                        if (
                            cand.cost_minor_per_serving is not None
                            and (Decimal(cand.cost_minor_per_serving) * Decimal("0.5")) > slot_budget
                        ):
                            removed += 1
                            continue
                        surviving.append(cand)
                    candidates = surviving
                    slot_filters_removed.append(
                        FilterRemovedCount(
                            filter=f"budget:{int(slot_budget)}", removed=removed
                        )
                    )
                    constraints_applied_summary["daily_budget"] += removed

                # If no candidates satisfy hard filters, return Infeasible response (AC-62, AC-72)
                if not candidates:
                    relaxable: list[str] = []
                    if payload.max_minutes is not None:
                        relaxable.append("max_minutes")
                    if payload.daily_budget_minor is not None:
                        relaxable.append("daily_budget")

                    return InfeasibleExplanationResponse(
                        status="infeasible",
                        slot=slot,
                        day=str(current_date),
                        filters=slot_filters_removed,
                        relaxable=relaxable,
                        message=f"No {slot} recipe satisfies all of your safety filters and limits.",
                    )

                # Variety & Repetition Constraint (AC-66)
                # With >= 10 eligible candidates, no recipe appears > 2 times in 7 days for the same slot,
                # and none on consecutive days for that slot.
                scored_candidates = candidates
                if len(candidates) >= 10:
                    filtered_for_variety = []
                    prev_recipe_id = previous_day_slot_recipe.get(slot)
                    for c in candidates:
                        if prev_recipe_id and c.id == prev_recipe_id:
                            continue
                        if recipe_plan_count[c.id] >= 2:
                            continue
                        filtered_for_variety.append(c)

                    if filtered_for_variety:
                        scored_candidates = filtered_for_variety

                # Candidate Evaluation & Scoring (AC-63, AC-64, AC-65)
                evaluated_list: list[tuple[Decimal, str, PreparedRecipe, Decimal]] = []
                for cand in scored_candidates:
                    # Discrete serving size selection (AC-64)
                    # With a daily budget, only sizes that fit the slot's share are allowed
                    # (D-30, AC-120); the budget filter above guarantees 0.5 fits
                    best_s = select_best_serving_size(
                        cand.per_serving_nutrients.calories,
                        slot_kcal if slot_kcal else Decimal("600"),
                        allowed_sizes=affordable_serving_sizes(
                            cand.cost_minor_per_serving, slot_budget
                        ),
                    )

                    cand_kcal = best_s * cand.per_serving_nutrients.calories
                    cand_protein = best_s * cand.per_serving_nutrients.protein_g

                    target_fit = calculate_target_fit(
                        cand_kcal=cand_kcal,
                        cand_protein=cand_protein,
                        slot_kcal=slot_kcal,
                        slot_protein=slot_protein,
                    )

                    c_pref = cuisine_prefs.get(cand.cuisine_code.lower(), "neutral")
                    if c_pref in ("favorite", "preferred"):
                        cuisine_match = Decimal("1.0")
                    elif c_pref == "like":
                        cuisine_match = Decimal("0.5")
                    elif c_pref == "avoid":
                        cuisine_match = Decimal("-1.0")
                    else:
                        cuisine_match = Decimal("0.0")

                    budget_ratio = (
                        (Decimal(cand.cost_minor_per_serving or 0) * best_s) / slot_budget
                        if (slot_budget and slot_budget > Decimal("0"))
                        else Decimal("0")
                    )

                    is_yesterday_repeat = (
                        previous_day_slot_recipe.get(slot) == cand.id
                    )
                    repetition_val = recipe_plan_count[cand.id] + (1 if is_yesterday_repeat else 0)

                    score = calculate_candidate_score(
                        target_fit=target_fit,
                        cuisine_match=cuisine_match,
                        total_minutes=cand.total_minutes,
                        budget_ratio=budget_ratio,
                        repetition=repetition_val,
                        weights=DEFAULT_WEIGHTS,
                    )

                    # AC-65: Equal scores tie-broken by recipe ID ascending
                    evaluated_list.append((score, str(cand.id), cand, best_s))

                # Deterministic sort: descending score, ascending recipe.id (AC-65)
                evaluated_list.sort(key=lambda x: (-x[0], x[1]))
                best_score, _, winning_cand, winning_s = evaluated_list[0]

                # Update tracking
                recipe_plan_count[winning_cand.id] += 1
                day_slot_recipes[slot] = winning_cand.id
                total_planned_meals_count += 1

                c_pref = cuisine_prefs.get(winning_cand.cuisine_code.lower(), "neutral")
                if c_pref in ("favorite", "preferred"):
                    preferred_cuisines_count += 1
                elif c_pref == "avoid":
                    used_avoid_cuisine = True

                # Scaled meal nutrients
                meal_nutrients = MealNutrientSummary(
                    calories=winning_s * winning_cand.per_serving_nutrients.calories,
                    protein_g=winning_s * winning_cand.per_serving_nutrients.protein_g,
                    carbs_g=winning_s * winning_cand.per_serving_nutrients.carbs_g,
                    fat_g=winning_s * winning_cand.per_serving_nutrients.fat_g,
                    fiber_g=winning_s * winning_cand.per_serving_nutrients.fiber_g,
                )

                meal_record = {
                    "plan_date": current_date,
                    "meal_type": slot,
                    "recipe": winning_cand,
                    "servings": winning_s,
                    "sort_order": slot_order,
                    "nutrients": meal_nutrients,
                }
                day_meals.append(meal_record)
                planned_meals_records.append(meal_record)

            # Update yesterday slot tracker for next day
            previous_day_slot_recipe = day_slot_recipes

            # Day Totals and Target Deviations (AC-67)
            day_kcal = sum((m["nutrients"].calories for m in day_meals), Decimal("0"))
            day_protein = sum((m["nutrients"].protein_g for m in day_meals), Decimal("0"))
            day_carbs = sum((m["nutrients"].carbs_g for m in day_meals), Decimal("0"))
            day_fat = sum((m["nutrients"].fat_g for m in day_meals), Decimal("0"))
            day_fiber = sum((m["nutrients"].fiber_g for m in day_meals), Decimal("0"))

            day_deviations: list[dict[str, Any]] = []
            is_within_range = True

            if active_goal.calorie_target_kcal:
                target_kcal = Decimal(str(active_goal.calorie_target_kcal))
                diff_kcal_pct = (day_kcal - target_kcal) / target_kcal
                if abs(diff_kcal_pct) > Decimal("0.10"):
                    is_within_range = False
                    dev_entry = {
                        "warning": "target_deviation",
                        "day": str(current_date),
                        "metric": "calories",
                        "target": active_goal.calorie_target_kcal,
                        "actual": int(round(day_kcal)),
                        "difference_pct": round(float(diff_kcal_pct * 100), 1),
                    }
                    day_deviations.append(dev_entry)
                    warnings.append(dev_entry)

            if active_goal.protein_target_g:
                target_protein = Decimal(str(active_goal.protein_target_g))
                if day_protein < Decimal("0.90") * target_protein:
                    is_within_range = False
                    diff_prot_pct = (day_protein - target_protein) / target_protein
                    dev_entry = {
                        "warning": "target_deviation",
                        "day": str(current_date),
                        "metric": "protein",
                        "target": active_goal.protein_target_g,
                        "actual": int(round(day_protein)),
                        "difference_pct": round(float(diff_prot_pct * 100), 1),
                    }
                    day_deviations.append(dev_entry)
                    warnings.append(dev_entry)

            planned_days_data.append(
                {
                    "plan_date": current_date,
                    "calories": day_kcal,
                    "protein_g": day_protein,
                    "carbs_g": day_carbs,
                    "fat_g": day_fat,
                    "fiber_g": day_fiber,
                    "calorie_target": active_goal.calorie_target_kcal,
                    "protein_target": active_goal.protein_target_g,
                    "is_within_range": is_within_range,
                    "deviations": day_deviations,
                }
            )

        # 6. Cuisine preference check (AC-61)
        preferred_cuisines_set = {
            c for c, p in cuisine_prefs.items() if p in ("favorite", "preferred")
        }
        if preferred_cuisines_set and total_planned_meals_count > 0:
            preferred_ratio = preferred_cuisines_count / total_planned_meals_count
            if preferred_ratio < 0.70 or used_avoid_cuisine:
                warnings.append(
                    {
                        "warning": "cuisine_preference_unmet",
                        "preferred_share_pct": round(preferred_ratio * 100, 1),
                        "used_avoided_cuisine": used_avoid_cuisine,
                        "message": "Fewer than 70% of meals match preferred cuisines or an avoided cuisine was used.",
                    }
                )

        # 7. Assemble target snapshot (AC-68)
        target_snapshot = {
            "targets": {
                "calorie_target_kcal": active_goal.calorie_target_kcal,
                "protein_target_g": active_goal.protein_target_g,
                "carbs_target_g": active_goal.carbs_target_g,
                "fat_target_g": active_goal.fat_target_g,
            },
            "constraints": {
                "allergies": sorted(list(user_allergies)),
                "diet_tags": sorted(list(user_diet_tags)),
                "excluded_ingredients": sorted(list(user_excluded)),
                "max_minutes": payload.max_minutes,
                "daily_budget_minor": payload.daily_budget_minor,
            },
            "weights": {k: str(v) for k, v in DEFAULT_WEIGHTS.items()},
            "catalog_version": "1.0",
        }

        # Explanation block (AC-72): share of the plan's nutrient values from approximate foods
        nutrient_values_total = 0
        nutrient_values_approximate = 0
        for m in planned_meals_records:
            for item_data in m["recipe"].ingredient_snapshots:
                n_values = len(item_data["nutrients_per_100g"])
                nutrient_values_total += n_values
                if item_data["approximate"]:
                    nutrient_values_approximate += n_values
        explanation = ExplanationBlock(
            constraints_applied=[
                {"filter": k, "removed_count": v} for k, v in constraints_applied_summary.items()
            ],
            scoring_weights={k: str(v) for k, v in DEFAULT_WEIGHTS.items()},
            generation_version="1.0",
            catalog_version="1.0",
            share_approximate_nutrients=(
                round(nutrient_values_approximate / nutrient_values_total, 4)
                if nutrient_values_total
                else 0.0
            ),
        )
        # Stored with the plan so later reads show the explanation as generated (D-09)
        target_snapshot["explanation"] = explanation.model_dump()

        # 8. Transactional persistence (AC-71)
        end_date = payload.start_date + timedelta(days=payload.days - 1)
        meal_plan = MealPlan(
            user_id=user_id,
            name=f"{payload.days}-Day Meal Plan",
            start_date=payload.start_date,
            end_date=end_date,
            status="ok",
            generation_version="1.0",
            target_snapshot=target_snapshot,
        )
        self.db.add(meal_plan)
        await self.db.flush()

        response_meals: list[PlannedMealResponse] = []
        for m in planned_meals_records:
            cand = m["recipe"]
            planned_meal = PlannedMeal(
                meal_plan_id=meal_plan.id,
                plan_date=m["plan_date"],
                meal_type=m["meal_type"],
                recipe_id=cand.id,
                title=cand.name,
                servings=m["servings"],
                sort_order=m["sort_order"],
            )
            self.db.add(planned_meal)
            await self.db.flush()

            response_items: list[PlannedMealItemResponse] = []
            for item_data in cand.ingredient_snapshots:
                scaled_qty = (item_data["quantity_base"] * m["servings"]) / cand.servings
                planned_item = PlannedMealItem(
                    planned_meal_id=planned_meal.id,
                    food_id=item_data["food_id"],
                    recipe_id=cand.id,
                    quantity=scaled_qty,
                    unit=item_data["unit"],
                    nutrient_snapshot=item_data["nutrients_per_100g"],
                )
                self.db.add(planned_item)
                await self.db.flush()

                response_items.append(
                    PlannedMealItemResponse(
                        id=planned_item.id,
                        food_id=item_data["food_id"],
                        ingredient_name=item_data["ingredient_name"],
                        quantity=scaled_qty,
                        unit=item_data["unit"],
                        nutrient_snapshot=item_data["nutrients_per_100g"],
                    )
                )

            cost_minor = None
            if cand.cost_minor_per_serving is not None:
                cost_minor = int(Decimal(cand.cost_minor_per_serving) * m["servings"])

            response_meals.append(
                PlannedMealResponse(
                    id=planned_meal.id,
                    plan_date=planned_meal.plan_date,
                    meal_type=planned_meal.meal_type,
                    recipe_id=planned_meal.recipe_id,
                    title=planned_meal.title,
                    servings=planned_meal.servings,
                    sort_order=planned_meal.sort_order,
                    cuisine_code=cand.cuisine_code,
                    total_minutes=cand.total_minutes,
                    cost_minor=cost_minor,
                    nutrients=m["nutrients"],
                    items=response_items,
                )
            )

        await self.db.commit()

        response_days = [
            DayNutrientTotal(
                plan_date=d["plan_date"],
                calories=d["calories"],
                protein_g=d["protein_g"],
                carbs_g=d["carbs_g"],
                fat_g=d["fat_g"],
                fiber_g=d["fiber_g"],
                calorie_target=d["calorie_target"],
                protein_target=d["protein_target"],
                is_within_range=d["is_within_range"],
                deviations=d["deviations"],
            )
            for d in planned_days_data
        ]

        return MealPlanResponse(
            id=meal_plan.id,
            name=meal_plan.name,
            start_date=meal_plan.start_date,
            end_date=meal_plan.end_date,
            status=meal_plan.status,
            generation_version=meal_plan.generation_version,
            target_snapshot=meal_plan.target_snapshot,
            meals=response_meals,
            days=response_days,
            warnings=warnings,
            explanation=explanation,
            disclaimer=DISCLAIMER_TEXT,
        )
