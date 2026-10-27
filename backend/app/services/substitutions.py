"""Substitution, manual edit, and grocery list aggregation services (spec §5.6, §5.7, FR-10, FR-11, AC-73–81)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.grocery import (
    GroceryItemInput,
    aggregate_grocery_items,
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
    PlannedMeal,
    PlannedMealItem,
    Recipe,
    RecipeIngredient,
)
from app.schemas.meal_plan import (
    GroceryItemResponse,
    GroceryListResponse,
    MealEditRequest,
    MealNutrientSummary,
    NutrientDifference,
    SubstitutionAcceptRequest,
    SubstitutionOptionResponse,
)
from app.services.planner import (
    PreparedRecipe,
    load_user_food_rules,
    slot_shares_for,
)

CUISINE_MATCH: dict[str, Decimal] = {
    "preferred": Decimal("1.0"),
    "like": Decimal("0.5"),
    "avoid": Decimal("-1.0"),
}


def _recipe_load_options() -> list:  # type: ignore[type-arg]
    return [
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food).selectinload(Food.nutrients),
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food).selectinload(Food.allergens),
        selectinload(Recipe.diet_tags),
        selectinload(Recipe.meal_types),
    ]


def _snapshot_items(meal: PlannedMeal, recipe: Recipe, servings: Decimal) -> list[PlannedMealItem]:
    """Planned items for a recipe at a serving count, with nutrient snapshots (D-09)."""
    items = []
    for ing in recipe.ingredients:
        nutrients_snapshot = {}
        if ing.food:
            nutrients_snapshot = {fn.nutrient_code: str(fn.amount_per_100g) for fn in ing.food.nutrients}
        items.append(
            PlannedMealItem(
                planned_meal_id=meal.id,
                food_id=ing.food_id,
                recipe_id=recipe.id,
                ingredient_name=ing.ingredient_name,
                quantity=(ing.quantity * servings) / recipe.servings,
                unit=ing.unit,
                nutrient_snapshot=nutrients_snapshot,
            )
        )
    return items


class SubstitutionService:
    """Handles meal substitutions, manual edits, and unit-aware grocery list generation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_plan_or_404(self, plan_id: UUID, user_id: UUID) -> MealPlan:
        stmt = (
            select(MealPlan)
            .where(MealPlan.id == plan_id, MealPlan.user_id == user_id)
            .options(
                selectinload(MealPlan.meals)
                .selectinload(PlannedMeal.items)
                .selectinload(PlannedMealItem.food)
                .selectinload(Food.nutrients),
                selectinload(MealPlan.meals)
                .selectinload(PlannedMeal.recipe)
                .selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food)
                .selectinload(Food.nutrients),
                selectinload(MealPlan.meals)
                .selectinload(PlannedMeal.recipe)
                .selectinload(Recipe.ingredients)
                .selectinload(RecipeIngredient.food)
                .selectinload(Food.allergens),
                selectinload(MealPlan.meals)
                .selectinload(PlannedMeal.recipe)
                .selectinload(Recipe.diet_tags),
            )
        )
        plan = (await self.db.execute(stmt)).scalars().first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meal_plan_not_found")
        return plan

    async def _load_recipe_for_user(self, recipe_id: UUID, user_id: UUID) -> Recipe:
        """A catalogue recipe or one of the user's own; anyone else's is not found (D-10)."""
        stmt = (
            select(Recipe)
            .where(
                Recipe.id == recipe_id,
                or_(Recipe.owner_user_id.is_(None), Recipe.owner_user_id == user_id),
            )
            .options(*_recipe_load_options())
        )
        recipe = (await self.db.execute(stmt)).scalars().first()
        if not recipe:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")
        return recipe

    async def _check_hard_constraints(self, recipe: Recipe, user_id: UUID) -> None:
        """Allergies, unverified allergen data, diet tags and exclusions are never
        overridden by a manual choice (S9, AC-75); time caps and cuisines are."""
        rules = await load_user_food_rules(self.db, user_id)
        broken = rules.violation(PreparedRecipe(recipe))
        if broken:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "violates_hard_constraint",
                    "constraint": broken,
                    "message": f"This recipe breaks one of your food rules ({broken}).",
                },
            )

    async def suggest_substitutions(
        self,
        user_id: UUID,
        plan_id: UUID,
        meal_id: UUID,
    ) -> list[SubstitutionOptionResponse]:
        """Suggest up to 5 valid replacement recipes scored against slot target (AC-73)."""
        plan = await self.get_plan_or_404(plan_id, user_id)
        current_meal = next((m for m in plan.meals if m.id == meal_id), None)
        if not current_meal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meal_not_found")

        rules = await load_user_food_rules(self.db, user_id)

        # Calculate current meal scaled nutrients
        curr_cal = Decimal("0")
        curr_prot = Decimal("0")
        curr_carbs = Decimal("0")
        curr_fat = Decimal("0")
        for it in current_meal.items:
            if it.nutrient_snapshot:
                factor = it.quantity / Decimal("100")
                curr_cal += factor * Decimal(str(it.nutrient_snapshot.get("energy_kcal", 0)))
                curr_prot += factor * Decimal(str(it.nutrient_snapshot.get("protein_g", 0)))
                curr_carbs += factor * Decimal(str(it.nutrient_snapshot.get("carbs_g", 0)))
                curr_fat += factor * Decimal(str(it.nutrient_snapshot.get("fat_g", 0)))

        # Load all candidate recipes
        recipes_stmt = (
            select(Recipe)
            .where(or_(Recipe.owner_user_id.is_(None), Recipe.owner_user_id == user_id))
            .options(*_recipe_load_options())
        )
        db_recipes = (await self.db.execute(recipes_stmt)).scalars().all()

        slot = current_meal.meal_type.lower()
        # The slot's share as the generator used it: over the slots planned that day
        day_slots = sorted(
            {m.meal_type.lower() for m in plan.meals if m.plan_date == current_meal.plan_date}
        )
        slot_share = slot_shares_for(day_slots)[slot]

        target_kcal = None
        target_prot = None
        if plan.target_snapshot and "targets" in plan.target_snapshot:
            t = plan.target_snapshot["targets"]
            if t.get("calorie_target_kcal"):
                target_kcal = Decimal(str(t["calorie_target_kcal"])) * slot_share
            if t.get("protein_target_g"):
                target_prot = Decimal(str(t["protein_target_g"])) * slot_share

        # The plan's user hard caps apply to substitutes too (spec 5.5 step 1.4, AC-73, D-30)
        caps = (plan.target_snapshot or {}).get("constraints", {})
        max_minutes = caps.get("max_minutes")
        daily_budget = caps.get("daily_budget_minor")
        slot_budget = Decimal(daily_budget) * slot_share if daily_budget is not None else None

        scored_options: list[tuple[Decimal, str, PreparedRecipe, Decimal]] = []

        for r in db_recipes:
            # AC-73: Exclude current recipe
            if r.id == current_meal.recipe_id:
                continue

            cand = PreparedRecipe(r)

            # Hard filters: slot compatibility, then the user's food rules (S9, AC-57-59)
            if slot not in cand.meal_types:
                continue
            if rules.violation(cand):
                continue

            # Hard filter: time and budget caps of the plan
            if max_minutes is not None and cand.total_minutes > max_minutes:
                continue
            sizes = affordable_serving_sizes(cand.cost_minor_per_serving, slot_budget)
            if not sizes:
                continue

            # Discrete serving size selection (AC-64), within the budget (D-30)
            best_s = select_best_serving_size(
                cand.per_serving_nutrients.calories,
                target_kcal if target_kcal else Decimal("600"),
                allowed_sizes=sizes,
            )

            cand_kcal = best_s * cand.per_serving_nutrients.calories
            cand_prot = best_s * cand.per_serving_nutrients.protein_g

            target_fit = calculate_target_fit(
                cand_kcal=cand_kcal,
                cand_protein=cand_prot,
                slot_kcal=target_kcal,
                slot_protein=target_prot,
            )

            cuisine_match = CUISINE_MATCH.get(rules.cuisine_pref(cand), Decimal("0.0"))

            score = calculate_candidate_score(
                target_fit=target_fit,
                cuisine_match=cuisine_match,
                total_minutes=cand.total_minutes,
                budget_ratio=Decimal("0"),
                repetition=0,
                weights=DEFAULT_WEIGHTS,
            )

            scored_options.append((score, str(cand.id), cand, best_s))

        # Sort descending by score, tie-break by recipe ID ascending (AC-65, AC-73)
        scored_options.sort(key=lambda x: (-x[0], x[1]))

        # Return at most 5 options (AC-73)
        top5 = scored_options[:5]
        results: list[SubstitutionOptionResponse] = []

        for score, _, cand, best_s in top5:
            cand_cal = best_s * cand.per_serving_nutrients.calories
            cand_prot = best_s * cand.per_serving_nutrients.protein_g
            cand_carbs = best_s * cand.per_serving_nutrients.carbs_g
            cand_fat = best_s * cand.per_serving_nutrients.fat_g
            cand_fib = best_s * cand.per_serving_nutrients.fiber_g

            diff = NutrientDifference(
                calories=cand_cal - curr_cal,
                protein_g=cand_prot - curr_prot,
                carbs_g=cand_carbs - curr_carbs,
                fat_g=cand_fat - curr_fat,
            )

            results.append(
                SubstitutionOptionResponse(
                    recipe_id=cand.id,
                    recipe_name=cand.name,
                    cuisine_code=cand.cuisine_code,
                    total_minutes=cand.total_minutes,
                    servings=best_s,
                    score=score,
                    nutrients=MealNutrientSummary(
                        calories=cand_cal,
                        protein_g=cand_prot,
                        carbs_g=cand_carbs,
                        fat_g=cand_fat,
                        fiber_g=cand_fib,
                    ),
                    nutrient_diff=diff,
                )
            )

        return results

    async def accept_substitution(
        self,
        user_id: UUID,
        plan_id: UUID,
        payload: SubstitutionAcceptRequest,
    ) -> None:
        """Replace meal recipe, recompute snapshot items, mark status edited (AC-74, AC-75)."""
        plan = await self.get_plan_or_404(plan_id, user_id)
        current_meal = next((m for m in plan.meals if m.id == payload.meal_id), None)
        if not current_meal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meal_not_found")

        recipe = await self._load_recipe_for_user(payload.recipe_id, user_id)
        await self._check_hard_constraints(recipe, user_id)

        current_meal.recipe_id = recipe.id
        current_meal.title = recipe.name
        current_meal.servings = payload.servings
        current_meal.items = _snapshot_items(current_meal, recipe, payload.servings)

        # Mark plan status edited (AC-74)
        plan.status = "edited"
        await self.db.commit()

    async def edit_meal(
        self,
        user_id: UUID,
        plan_id: UUID,
        meal_id: UUID,
        payload: MealEditRequest,
    ) -> None:
        """Edit planned meal servings or recipe with hard safety validation (AC-75, AC-76)."""
        plan = await self.get_plan_or_404(plan_id, user_id)
        current_meal = next((m for m in plan.meals if m.id == meal_id), None)
        if not current_meal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meal_not_found")

        # Range check servings (AC-76: 0.5 to 10 accepted; 0, -1, 11 rejected)
        servings_to_use = payload.servings if payload.servings is not None else current_meal.servings
        if servings_to_use < Decimal("0.5") or servings_to_use > Decimal("10.0"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="servings_out_of_range",
            )

        recipe_to_use = current_meal.recipe
        if payload.recipe_id is not None and payload.recipe_id != current_meal.recipe_id:
            recipe_to_use = await self._load_recipe_for_user(payload.recipe_id, user_id)
            await self._check_hard_constraints(recipe_to_use, user_id)
            current_meal.recipe_id = recipe_to_use.id
            current_meal.title = recipe_to_use.name

        current_meal.servings = servings_to_use

        # Re-snapshot items if recipe exists
        if recipe_to_use:
            current_meal.items = _snapshot_items(current_meal, recipe_to_use, servings_to_use)

        plan.status = "edited"
        await self.db.commit()

    async def get_grocery_list(
        self,
        user_id: UUID,
        plan_id: UUID,
        from_date: date | None,
        to_date: date | None,
    ) -> GroceryListResponse:
        """Unit-aware grocery list aggregated across chosen dates (spec §5.7, AC-77–81)."""
        plan = await self.get_plan_or_404(plan_id, user_id)

        # Date range filtering (AC-80)
        filtered_meals = plan.meals
        if from_date is not None:
            filtered_meals = [m for m in filtered_meals if m.plan_date >= from_date]
        if to_date is not None:
            filtered_meals = [m for m in filtered_meals if m.plan_date <= to_date]

        # If date range is empty, return empty list with status 200 (AC-80)
        if not filtered_meals or (from_date and to_date and from_date > to_date):
            return GroceryListResponse(
                plan_id=plan.id,
                from_date=from_date,
                to_date=to_date,
                items=[],
            )

        grocery_inputs: list[GroceryItemInput] = []

        for meal in filtered_meals:
            for item in meal.items:
                food_category = "general"
                is_text_only = item.food_id is None
                food_id_str = str(item.food_id) if item.food_id else None
                name = item.food.name if item.food else (item.ingredient_name or "Ingredient")

                if item.food:
                    food_category = item.food.food_category

                grocery_inputs.append(
                    GroceryItemInput(
                        name=name,
                        quantity=item.quantity,
                        unit=item.unit,
                        food_id=food_id_str,
                        category=food_category,
                        is_text_only=is_text_only,
                    )
                )

        aggregated = aggregate_grocery_items(grocery_inputs)

        items_resp: list[GroceryItemResponse] = [
            GroceryItemResponse(
                name=agg.name,
                total_quantity=agg.total_quantity,
                canonical_unit=agg.canonical_unit,
                unit_family=agg.unit_family.value,
                display_quantity=agg.display_quantity,
                food_id=UUID(agg.food_id) if agg.food_id else None,
                category=agg.category,
                is_text_only=agg.is_text_only,
            )
            for agg in aggregated
        ]

        return GroceryListResponse(
            plan_id=plan.id,
            from_date=from_date,
            to_date=to_date,
            items=items_resp,
        )
