"""Catalogue API routes for exercises, foods, and recipes (spec §6, FR-02, FR-06, AC-29, AC-30, AC-49, AC-52, AC-53, AC-55)."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user_optional,
    get_current_user_required,
    get_db,
    verify_csrf,
)
from app.domain.nutrients import (
    NutrientProfile,
    RecipeIngredientInput,
    calculate_recipe_nutrients,
)
from app.models.nutrition import (
    Food,
    NutritionLogItem,
    PlannedMealItem,
    Recipe,
    RecipeDietTag,
    RecipeIngredient,
    RecipeMealType,
)
from app.models.user import User
from app.models.workout import Exercise
from app.schemas.catalogue import (
    ExerciseCreateRequest,
    ExerciseResponse,
    FoodNutrientSchema,
    FoodResponse,
    RecipeIngredientResponse,
    RecipeNutritionResponse,
    RecipeResponse,
)

router = APIRouter(prefix="/api", tags=["catalogue"])


# ---------------------------------------------------------------------------
# Exercises Endpoints (FR-02, AC-29, AC-30)
# ---------------------------------------------------------------------------


@router.get("/exercises", response_model=list[ExerciseResponse])
async def list_exercises(
    q: str | None = Query(None, description="Case-insensitive substring search"),
    muscle: str | None = Query(None, description="Primary muscle group filter"),
    equipment: str | None = Query(None, description="Equipment filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> list[ExerciseResponse]:
    """Search and filter exercise catalogue with pagination (AC-29)."""
    user_id = current_user.id if current_user else None
    stmt = select(Exercise).where(
        or_(
            Exercise.owner_user_id.is_(None),
            Exercise.owner_user_id == user_id,
        )
    )

    if q:
        stmt = stmt.where(Exercise.name.ilike(f"%{q.strip()}%"))
    if muscle:
        stmt = stmt.where(Exercise.primary_muscle.ilike(muscle.strip()))
    if equipment:
        stmt = stmt.where(Exercise.equipment.ilike(equipment.strip()))

    stmt = stmt.order_by(Exercise.name.asc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    exercises = result.scalars().all()

    return [
        ExerciseResponse(
            id=ex.id,
            name=ex.name,
            primary_muscle=ex.primary_muscle,
            equipment=ex.equipment,
            movement_pattern=ex.movement_pattern,
            instructions=ex.instructions,
            is_custom=ex.is_custom,
        )
        for ex in exercises
    ]


@router.post("/exercises", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_exercise(
    payload: ExerciseCreateRequest,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> ExerciseResponse:
    """Create a user-owned custom exercise (AC-29, AC-30).

    Name must be unique per owner (case-insensitive), otherwise 409.
    """
    clean_name = payload.name.strip()
    # Check if this user already has an exercise with this name
    existing = await db.execute(
        select(Exercise).where(
            Exercise.owner_user_id == current_user.id,
            func.lower(Exercise.name) == clean_name.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="exercise_already_exists",
        )

    exercise = Exercise(
        name=clean_name,
        primary_muscle=payload.primary_muscle.strip(),
        equipment=payload.equipment.strip(),
        movement_pattern=payload.movement_pattern.strip(),
        instructions=payload.instructions.strip() if payload.instructions else None,
        is_custom=True,
        owner_user_id=current_user.id,
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)

    return ExerciseResponse(
        id=exercise.id,
        name=exercise.name,
        primary_muscle=exercise.primary_muscle,
        equipment=exercise.equipment,
        movement_pattern=exercise.movement_pattern,
        instructions=exercise.instructions,
        is_custom=exercise.is_custom,
    )


# ---------------------------------------------------------------------------
# Foods Endpoints (FR-06, AC-49, AC-50, AC-55)
# ---------------------------------------------------------------------------


def _map_food_to_response(food: Food) -> FoodResponse:
    nutrients = [
        FoodNutrientSchema(
            nutrient_code=fn.nutrient_code,
            amount_per_100g=fn.amount_per_100g,
            unit=fn.unit,
        )
        for fn in food.nutrients
    ]
    allergens = [fa.allergen_code for fa in food.allergens]
    return FoodResponse(
        id=food.id,
        name=food.name,
        food_category=food.food_category,
        cuisine_code=food.cuisine_code,
        serving_description=food.serving_description,
        default_serving_g=food.default_serving_g,
        state=food.state,
        approximate=food.approximate,
        allergens_verified=food.allergens_verified,
        data_source=food.data_source,
        source_reference=food.source_reference,
        verified_at=food.verified_at,
        nutrients=nutrients,
        allergens=allergens,
    )


@router.get("/foods", response_model=list[FoodResponse])
async def list_foods(
    q: str | None = Query(None, description="Food name substring search"),
    category: str | None = Query(None, description="Food category filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[FoodResponse]:
    """Search foods with nutrients, provenance, and approximate labelling (AC-49, AC-53)."""
    stmt = (
        select(Food)
        .options(selectinload(Food.nutrients), selectinload(Food.allergens))
        .order_by(Food.name.asc())
    )
    if q:
        stmt = stmt.where(Food.name.ilike(f"%{q.strip()}%"))
    if category:
        stmt = stmt.where(Food.food_category.ilike(category.strip()))

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    foods = result.scalars().all()
    return [_map_food_to_response(f) for f in foods]


@router.get("/foods/{food_id}", response_model=FoodResponse)
async def get_food(food_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> FoodResponse:
    stmt = (
        select(Food)
        .options(selectinload(Food.nutrients), selectinload(Food.allergens))
        .where(Food.id == food_id)
    )
    result = await db.execute(stmt)
    food = result.scalar_one_or_none()
    if not food:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="food_not_found")
    return _map_food_to_response(food)


@router.delete("/foods/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(
    food_id: uuid.UUID,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a food item, refusing with 409 if referenced in history or recipes (AC-55)."""
    # Check recipe ingredients
    rec_ref = await db.execute(
        select(RecipeIngredient.id).where(RecipeIngredient.food_id == food_id).limit(1)
    )
    if rec_ref.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="food_referenced_in_recipe",
        )

    # Check planned meal items
    plan_ref = await db.execute(
        select(PlannedMealItem.id).where(PlannedMealItem.food_id == food_id).limit(1)
    )
    if plan_ref.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="food_referenced_in_history",
        )

    # Check nutrition log items
    log_ref = await db.execute(
        select(NutritionLogItem.id).where(NutritionLogItem.food_id == food_id).limit(1)
    )
    if log_ref.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="food_referenced_in_history",
        )

    # Fetch food
    food = await db.get(Food, food_id)
    if not food:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="food_not_found")

    await db.delete(food)
    await db.commit()


# ---------------------------------------------------------------------------
# Recipes Endpoints (FR-06, AC-51, AC-52, AC-53)
# ---------------------------------------------------------------------------


def _calculate_recipe_response(recipe: Recipe) -> RecipeResponse:
    # 1. Map ingredients and assemble domain inputs
    ingredient_responses: list[RecipeIngredientResponse] = []
    domain_inputs: list[RecipeIngredientInput] = []
    allergen_set: set[str] = set()
    has_incomplete_allergens = False

    for ing in recipe.ingredients:
        ingredient_responses.append(
            RecipeIngredientResponse(
                id=ing.id,
                food_id=ing.food_id,
                ingredient_name=ing.ingredient_name,
                quantity=ing.quantity,
                unit=ing.unit,
                edible_weight_g=ing.edible_weight_g,
            )
        )

        if ing.food:
            # Check allergens
            if not ing.food.allergens_verified:
                has_incomplete_allergens = True
            for fa in ing.food.allergens:
                allergen_set.add(fa.allergen_code)

            # Build nutrient profile per 100g
            nutrients_dict: dict[str, Decimal] = {}
            for fn in ing.food.nutrients:
                nutrients_dict[fn.nutrient_code] = fn.amount_per_100g

            profile = NutrientProfile(
                calories=nutrients_dict.get("energy_kcal", Decimal("0")),
                protein_g=nutrients_dict.get("protein_g", Decimal("0")),
                carbs_g=nutrients_dict.get("carbs_g", Decimal("0")),
                fat_g=nutrients_dict.get("fat_g", Decimal("0")),
                fiber_g=nutrients_dict.get("fiber_g", Decimal("0")),
            )
            domain_inputs.append(
                RecipeIngredientInput(
                    food_nutrients=profile,
                    quantity_g=ing.quantity,
                    edible_weight_g=ing.edible_weight_g,
                )
            )
        else:
            # Text-only ingredient: allergen status is incomplete (AC-52)
            has_incomplete_allergens = True

    # 2. Domain calculation for per-serving nutrients
    if domain_inputs and recipe.servings > Decimal("0"):
        calc_result = calculate_recipe_nutrients(domain_inputs, recipe.servings)
        nutrition_resp = RecipeNutritionResponse(
            calories=calc_result.per_serving.calories,
            protein_g=calc_result.per_serving.protein_g,
            carbs_g=calc_result.per_serving.carbs_g,
            fat_g=calc_result.per_serving.fat_g,
            fiber_g=calc_result.per_serving.fiber_g,
        )
    else:
        nutrition_resp = RecipeNutritionResponse(
            calories=Decimal("0"),
            protein_g=Decimal("0"),
            carbs_g=Decimal("0"),
            fat_g=Decimal("0"),
            fiber_g=Decimal("0"),
        )

    diet_tags = [dt.diet_tag for dt in recipe.diet_tags]
    meal_types = [rmt.meal_type for rmt in recipe.meal_types]

    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        cuisine_code=recipe.cuisine_code,
        instructions=recipe.instructions,
        prep_minutes=recipe.prep_minutes,
        cook_minutes=recipe.cook_minutes,
        total_minutes=recipe.prep_minutes + recipe.cook_minutes,
        servings=recipe.servings,
        cost_minor_per_serving=recipe.cost_minor_per_serving,
        cost_currency=recipe.cost_currency,
        diet_tags=diet_tags,
        meal_types=meal_types,
        ingredients=ingredient_responses,
        per_serving_nutrients=nutrition_resp,
        allergens=sorted(list(allergen_set)),
        has_incomplete_allergen_data=has_incomplete_allergens,
    )


@router.get("/recipes", response_model=list[RecipeResponse])
async def list_recipes(
    q: str | None = Query(None, description="Recipe name substring search"),
    cuisine: str | None = Query(None, description="Cuisine filter (e.g. indian, italian)"),
    diet_tag: str | None = Query(None, description="Diet tag filter (e.g. vegetarian, vegan)"),
    meal_type: str | None = Query(None, description="Meal slot filter (e.g. breakfast, lunch)"),
    max_time: int | None = Query(None, ge=1, description="Max total time (prep + cook) in minutes"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[RecipeResponse]:
    """Search and filter recipes catalogue with pagination and per-serving nutrition (AC-53)."""
    stmt = (
        select(Recipe)
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
        .order_by(Recipe.name.asc())
    )

    if q:
        stmt = stmt.where(Recipe.name.ilike(f"%{q.strip()}%"))
    if cuisine:
        stmt = stmt.where(Recipe.cuisine_code.ilike(cuisine.strip()))
    if max_time is not None:
        stmt = stmt.where((Recipe.prep_minutes + Recipe.cook_minutes) <= max_time)
    if diet_tag:
        stmt = stmt.join(Recipe.diet_tags).where(RecipeDietTag.diet_tag.ilike(diet_tag.strip()))
    if meal_type:
        stmt = stmt.join(Recipe.meal_types).where(RecipeMealType.meal_type.ilike(meal_type.strip()))

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    recipes = result.scalars().all()
    return [_calculate_recipe_response(r) for r in recipes]


@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RecipeResponse:
    stmt = (
        select(Recipe)
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
        .where(Recipe.id == recipe_id)
    )
    result = await db.execute(stmt)
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recipe_not_found")
    return _calculate_recipe_response(recipe)
