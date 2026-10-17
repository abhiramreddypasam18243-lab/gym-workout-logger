"""Initial database schema migration (spec §6, AC-97).

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-17 10:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # 2. sessions
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index("idx_sessions_token_hash", "sessions", ["token_hash"])

    # 3. user_profiles
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("display_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("height_cm", sa.Numeric(5, 1), nullable=True),
        sa.Column("body_weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("units", sa.String(2), nullable=False, server_default="kg"),
        sa.Column("sex_for_estimate", sa.String(20), nullable=False, server_default="unspecified"),
        sa.Column("adult_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "needs_professional_guidance", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("calories_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("nutrition_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("track_body_weight", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("weekly_session_target", sa.Integer(), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("goal", sa.String(30), nullable=False, server_default="maintain"),
        sa.Column("activity_level", sa.String(30), nullable=False, server_default="moderate"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("height_cm >= 50 AND height_cm <= 260", name="chk_profile_height"),
        sa.CheckConstraint(
            "body_weight_kg >= 20 AND body_weight_kg <= 400", name="chk_profile_weight"
        ),
        sa.CheckConstraint("units IN ('kg', 'lb')", name="chk_profile_units"),
        sa.CheckConstraint("goal IN ('maintain', 'build_strength')", name="chk_profile_goal"),
    )

    # 4. user_food_constraints
    op.create_table(
        "user_food_constraints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("constraint_type", sa.String(30), nullable=False),
        sa.Column("constraint_value", sa.String(100), nullable=False),
        sa.Column("is_hard_constraint", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "constraint_type IN ('allergy', 'diet_tag', 'excluded_ingredient')",
            name="chk_constraint_type",
        ),
    )
    op.create_index("idx_food_constraints_user_id", "user_food_constraints", ["user_id"])

    # 5. user_cuisine_preferences
    op.create_table(
        "user_cuisine_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cuisine_code", sa.String(50), nullable=False),
        sa.Column("preference_level", sa.String(20), nullable=False, server_default="neutral"),
        sa.UniqueConstraint("user_id", "cuisine_code", name="uq_user_cuisine"),
        sa.CheckConstraint(
            "preference_level IN ('preferred', 'like', 'neutral', 'avoid')",
            name="chk_preference_level",
        ),
    )
    op.create_index("idx_cuisine_prefs_user_id", "user_cuisine_preferences", ["user_id"])

    # 6. exercises
    op.create_table(
        "exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("primary_muscle", sa.String(50), nullable=False),
        sa.Column("equipment", sa.String(50), nullable=False),
        sa.Column("movement_pattern", sa.String(50), nullable=False, server_default=""),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_exercises_name", "exercises", ["name"])
    op.create_index("idx_exercises_muscle", "exercises", ["primary_muscle"])
    op.create_index("idx_exercises_equipment", "exercises", ["equipment"])

    # 7. workout_routines
    op.create_table(
        "workout_routines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_routines_user_id", "workout_routines", ["user_id"])

    # 8. routine_exercises
    op.create_table(
        "routine_exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "routine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workout_routines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exercises.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("target_sets", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("rep_min", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("rep_max", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.CheckConstraint("rep_min <= rep_max", name="chk_routine_rep_range"),
        sa.CheckConstraint("target_sets > 0", name="chk_routine_target_sets"),
        sa.CheckConstraint("rep_min > 0", name="chk_routine_rep_min"),
    )
    op.create_index("idx_routine_exercises_routine_id", "routine_exercises", ["routine_id"])

    # 9. workout_sessions
    op.create_table(
        "workout_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "routine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workout_routines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_workout_sessions_user_started", "workout_sessions", ["user_id", "started_at"]
    )

    # 10. workout_exercises
    op.create_table(
        "workout_exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workout_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("exercises.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("idx_workout_exercises_session_id", "workout_exercises", ["session_id"])

    # 11. workout_sets
    op.create_table(
        "workout_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workout_exercise_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workout_exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("load_kg", sa.Numeric(6, 2), nullable=False),
        sa.Column("rpe", sa.Numeric(3, 1), nullable=True),
        sa.Column("is_warmup", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workout_exercise_id", "set_number", name="uq_exercise_set_number"),
        sa.CheckConstraint("reps > 0", name="chk_set_reps_positive"),
        sa.CheckConstraint("load_kg >= 0", name="chk_set_load_non_negative"),
        sa.CheckConstraint("rpe IS NULL OR (rpe >= 1.0 AND rpe <= 10.0)", name="chk_set_rpe_range"),
    )
    op.create_index("idx_workout_sets_exercise_id", "workout_sets", ["workout_exercise_id"])

    # 12. foods
    op.create_table(
        "foods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("food_category", sa.String(50), nullable=False),
        sa.Column("cuisine_code", sa.String(50), nullable=True),
        sa.Column("serving_description", sa.String(100), nullable=False),
        sa.Column("default_serving_g", sa.Numeric(6, 2), nullable=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="raw"),
        sa.Column("approximate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allergens_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("data_source", sa.String(100), nullable=False),
        sa.Column("source_reference", sa.String(200), nullable=True),
        sa.Column("verified_at", sa.Date(), nullable=True),
    )
    op.create_index("idx_foods_name", "foods", ["name"])
    op.create_index("idx_foods_category", "foods", ["food_category"])

    # 13. food_nutrients
    op.create_table(
        "food_nutrients",
        sa.Column(
            "food_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("nutrient_code", sa.String(30), primary_key=True),
        sa.Column("amount_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("unit", sa.String(10), nullable=False, server_default="g"),
        sa.CheckConstraint("amount_per_100g >= 0", name="chk_nutrient_amount_non_negative"),
    )

    # 14. food_allergens
    op.create_table(
        "food_allergens",
        sa.Column(
            "food_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("allergen_code", sa.String(50), primary_key=True),
    )

    # 15. recipes
    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("cuisine_code", sa.String(50), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("prep_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cook_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("servings", sa.Numeric(4, 1), nullable=False, server_default="1.0"),
        sa.Column("cost_minor_per_serving", sa.Integer(), nullable=True),
        sa.Column("cost_currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.CheckConstraint("prep_minutes >= 0", name="chk_recipe_prep_time"),
        sa.CheckConstraint("cook_minutes >= 0", name="chk_recipe_cook_time"),
        sa.CheckConstraint("servings > 0", name="chk_recipe_servings_positive"),
    )
    op.create_index("idx_recipes_name", "recipes", ["name"])
    op.create_index("idx_recipes_cuisine", "recipes", ["cuisine_code"])

    # 16. recipe_ingredients
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "food_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("ingredient_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(8, 2), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("edible_weight_g", sa.Numeric(8, 2), nullable=True),
        sa.CheckConstraint("quantity > 0", name="chk_ingredient_qty_positive"),
    )
    op.create_index("idx_recipe_ingredients_recipe_id", "recipe_ingredients", ["recipe_id"])

    # 17. recipe_diet_tags
    op.create_table(
        "recipe_diet_tags",
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("diet_tag", sa.String(50), primary_key=True),
    )

    # 18. recipe_meal_types
    op.create_table(
        "recipe_meal_types",
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("meal_type", sa.String(30), primary_key=True),
    )

    # 19. nutrition_goals
    op.create_table(
        "nutrition_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("calorie_target_kcal", sa.Integer(), nullable=True),
        sa.Column("protein_target_g", sa.Integer(), nullable=True),
        sa.Column("carbs_target_g", sa.Integer(), nullable=True),
        sa.Column("fat_target_g", sa.Integer(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "calorie_target_kcal IS NULL OR calorie_target_kcal > 0",
            name="chk_target_calories_positive",
        ),
    )
    op.create_index(
        "idx_nutrition_goals_user_date", "nutrition_goals", ["user_id", "effective_from"]
    )

    # 20. meal_plans
    op.create_table(
        "meal_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False, server_default="7-Day Meal Plan"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),
        sa.Column("generation_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("target_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_meal_plans_user_start", "meal_plans", ["user_id", "start_date"])

    # 21. planned_meals
    op.create_table(
        "planned_meals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meal_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meal_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(30), nullable=False),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("servings", sa.Numeric(4, 1), nullable=False, server_default="1.0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("servings > 0", name="chk_planned_servings_positive"),
    )
    op.create_index("idx_planned_meals_plan_id", "planned_meals", ["meal_plan_id"])

    # 22. planned_meal_items
    op.create_table(
        "planned_meal_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "planned_meal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planned_meals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "food_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Numeric(8, 2), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("nutrient_snapshot", sa.JSON(), nullable=True),
    )
    op.create_index("idx_planned_meal_items_meal_id", "planned_meal_items", ["planned_meal_id"])

    # 23. nutrition_logs
    op.create_table(
        "nutrition_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meal_type", sa.String(30), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="food"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_nutrition_logs_user_consumed", "nutrition_logs", ["user_id", "consumed_at"]
    )

    # 24. nutrition_log_items
    op.create_table(
        "nutrition_log_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "nutrition_log_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nutrition_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "food_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Numeric(8, 2), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("nutrient_snapshot", sa.JSON(), nullable=True),
    )
    op.create_index("idx_nutrition_log_items_log_id", "nutrition_log_items", ["nutrition_log_id"])


def downgrade() -> None:
    op.drop_table("nutrition_log_items")
    op.drop_table("nutrition_logs")
    op.drop_table("planned_meal_items")
    op.drop_table("planned_meals")
    op.drop_table("meal_plans")
    op.drop_table("nutrition_goals")
    op.drop_table("recipe_meal_types")
    op.drop_table("recipe_diet_tags")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("food_allergens")
    op.drop_table("food_nutrients")
    op.drop_table("foods")
    op.drop_table("workout_sets")
    op.drop_table("workout_exercises")
    op.drop_table("workout_sessions")
    op.drop_table("routine_exercises")
    op.drop_table("workout_routines")
    op.drop_table("exercises")
    op.drop_table("user_cuisine_preferences")
    op.drop_table("user_food_constraints")
    op.drop_table("user_profiles")
    op.drop_table("sessions")
    op.drop_table("users")
