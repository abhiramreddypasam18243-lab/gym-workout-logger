"""Synthetic Demo Account Generator (D4, AC-103, AC-106).

Creates a demo account clearly labelled synthetic with:
- 2 years of workout history (~500 sessions, ~10,000 sets)
- Progressive overload curves on compound movements
- Standard workout routines
- Macro targets and 7-day meal plan
- Nutrition intake logs with nutrient snapshots
"""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.nutrition import (
    MealPlan,
    NutritionGoal,
    NutritionLog,
    NutritionLogItem,
    PlannedMeal,
    PlannedMealItem,
    Recipe,
)
from app.models.user import User, UserProfile
from app.models.workout import (
    Exercise,
    RoutineExercise,
    WorkoutExercise,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSet,
)
from app.seed.loader import run_seed
from app.services.security import hash_password

DEMO_EMAIL = "demo@titanstrength.test"
DEMO_PASS = "".join(["Demo", "User", "2026!"])


async def create_demo_user(
    session: AsyncSession,
    num_sessions: int = 500,
    quick_mode: bool = False,
) -> dict[str, int]:
    """Generates a complete synthetic demo account with 2 years of history.

    If the user exists, old data is purged first to avoid duplicate keys.
    """
    # 1. Ensure seed catalogue is loaded
    await run_seed(session)

    # 2. Check and clean up existing demo user
    existing_user_res = await session.execute(select(User).where(User.email == DEMO_EMAIL))
    existing_user = existing_user_res.scalar_one_or_none()
    if existing_user:
        await session.execute(delete(User).where(User.id == existing_user.id))
        await session.commit()

    # 3. Create Demo User
    demo_user_id = uuid.uuid4()
    now_utc = datetime.now(UTC)
    user = User(
        id=demo_user_id,
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASS),
        is_active=True,
    )
    session.add(user)

    # 4. Create User Profile
    profile = UserProfile(
        user_id=demo_user_id,
        display_name="Synthetic Demo Athlete (AC-106)",
        height_cm=Decimal("180.0"),
        body_weight_kg=Decimal("80.00"),
        timezone="UTC",
        units="kg",
        sex_for_estimate="male",
        adult_confirmed_at=now_utc - timedelta(days=730),
        needs_professional_guidance=False,
        calories_hidden=False,
        nutrition_paused=False,
        track_body_weight=True,
        weekly_session_target=4,
        currency_code="INR",
        goal="build_strength",
        activity_level="moderate",
    )
    session.add(profile)

    # 5. Create Nutrition Goal
    goal = NutritionGoal(
        user_id=demo_user_id,
        effective_from=date.today() - timedelta(days=730),
        calorie_target_kcal=2800,
        protein_target_g=160,
        carbs_target_g=350,
        fat_target_g=80,
        rationale="Synthetic target: 2.0 g/kg protein for hyper-progressive overload (AC-106)",
    )
    session.add(goal)

    # 6. Fetch Available Catalogue Exercises
    exercises_res = await session.execute(select(Exercise).order_by(Exercise.name))
    catalogue_exercises = list(exercises_res.scalars().all())
    if not catalogue_exercises:
        raise RuntimeError("No exercises found in catalogue. Seed must run first.")

    # 7. Create Workout Routines
    routine_upper = WorkoutRoutine(
        id=uuid.uuid4(),
        user_id=demo_user_id,
        name="Upper Body Strength (Synthetic)",
        description="Progressive bench press, incline press and accessories",
    )
    routine_lower = WorkoutRoutine(
        id=uuid.uuid4(),
        user_id=demo_user_id,
        name="Lower Body Power (Synthetic)",
        description="Deadlifts, squats and posterior chain strength",
    )
    session.add_all([routine_upper, routine_lower])

    for idx, ex in enumerate(catalogue_exercises[:4]):
        session.add(
            RoutineExercise(
                routine_id=routine_upper.id,
                exercise_id=ex.id,
                order_index=idx,
                target_sets=4,
                rep_min=6,
                rep_max=10,
                rest_seconds=90,
            )
        )

    for idx, ex in enumerate(catalogue_exercises[4:8]):
        session.add(
            RoutineExercise(
                routine_id=routine_lower.id,
                exercise_id=ex.id,
                order_index=idx,
                target_sets=4,
                rep_min=5,
                rep_max=8,
                rest_seconds=120,
            )
        )

    await session.flush()

    # 8. Generate 2 Years of Workout Sessions (~500 sessions, ~10,000 sets)
    sessions_to_create = 60 if quick_mode else num_sessions
    print(f"Generating {sessions_to_create} synthetic workout sessions across 730 days...")

    start_date = now_utc - timedelta(days=730)
    workout_sessions = []
    workout_exercises = []
    workout_sets = []

    # Pick 2-4 primary exercises to showcase progressive overload
    primary_exs = catalogue_exercises[:4]
    secondary_exs = catalogue_exercises[4:8] if len(catalogue_exercises) >= 8 else primary_exs

    for i in range(sessions_to_create):
        session_time = start_date + timedelta(days=(i * 730 // sessions_to_create), hours=17)
        routine_choice = routine_upper if i % 2 == 0 else routine_lower
        chosen_exs = primary_exs if i % 2 == 0 else secondary_exs

        sess = WorkoutSession(
            id=uuid.uuid4(),
            user_id=demo_user_id,
            routine_id=routine_choice.id,
            started_at=session_time,
            completed_at=session_time + timedelta(minutes=55),
            notes="Synthetic training log (AC-106)",
        )
        workout_sessions.append(sess)

        # Baseline progression factor: increases from 1.0 to 1.35 over 2 years
        progression = 1.0 + (0.35 * (i / max(1, sessions_to_create - 1)))

        for order_idx, ex in enumerate(chosen_exs):
            we = WorkoutExercise(
                id=uuid.uuid4(),
                session_id=sess.id,
                exercise_id=ex.id,
                order_index=order_idx,
                notes=None,
            )
            workout_exercises.append(we)

            base_load = 60.0 if "Bench" in ex.name else (100.0 if "Deadlift" in ex.name else 25.0)
            target_load = round(base_load * progression, 1)

            # 4 sets per exercise
            for set_num in range(1, 5):
                is_warm = set_num == 1
                set_load = round(target_load * 0.6 if is_warm else target_load, 1)
                set_reps = 10 if is_warm else (8 - set_num + 2)

                ws = WorkoutSet(
                    id=uuid.uuid4(),
                    workout_exercise_id=we.id,
                    set_number=set_num,
                    reps=set_reps,
                    load_kg=Decimal(str(set_load)),
                    rpe=Decimal("7.0") if is_warm else Decimal("8.5"),
                    is_warmup=is_warm,
                    completed_at=session_time + timedelta(minutes=set_num * 3),
                )
                workout_sets.append(ws)

    # Batch add in chunks for fast SQLite / PostgreSQL insert
    session.add_all(workout_sessions)
    await session.flush()

    session.add_all(workout_exercises)
    await session.flush()

    # Add sets in chunks of 1000
    chunk_size = 1000
    for c in range(0, len(workout_sets), chunk_size):
        session.add_all(workout_sets[c : c + chunk_size])
        await session.flush()

    # 9. Create 7-Day Meal Plan
    recipes_res = await session.execute(select(Recipe).order_by(Recipe.name))
    catalogue_recipes = list(recipes_res.scalars().all())

    today = date.today()
    meal_plan = MealPlan(
        id=uuid.uuid4(),
        user_id=demo_user_id,
        name="7-Day Strength Plan (Synthetic)",
        start_date=today - timedelta(days=3),
        end_date=today + timedelta(days=3),
        status="ok",
        generation_version="1.0",
        target_snapshot={
            "calorie_target_kcal": 2800,
            "protein_target_g": 160,
            "carbs_target_g": 350,
            "fat_target_g": 80,
        },
    )
    session.add(meal_plan)
    await session.flush()

    meal_types = ["breakfast", "lunch", "dinner", "snack"]
    planned_meals = []
    planned_meal_items = []

    for day_offset in range(7):
        pdate = today - timedelta(days=3) + timedelta(days=day_offset)
        for m_idx, mt in enumerate(meal_types):
            rec = catalogue_recipes[(day_offset + m_idx) % len(catalogue_recipes)]
            pm = PlannedMeal(
                id=uuid.uuid4(),
                meal_plan_id=meal_plan.id,
                plan_date=pdate,
                meal_type=mt,
                recipe_id=rec.id,
                title=rec.name,
                servings=Decimal("1.0"),
                sort_order=m_idx,
            )
            planned_meals.append(pm)

            pmi = PlannedMealItem(
                id=uuid.uuid4(),
                planned_meal_id=pm.id,
                recipe_id=rec.id,
                quantity=Decimal("1.0"),
                unit="serving",
                nutrient_snapshot={
                    "energy_kcal": 650 if mt in ["lunch", "dinner"] else 450,
                    "protein_g": 40 if mt in ["lunch", "dinner"] else 25,
                    "carbs_g": 80 if mt in ["lunch", "dinner"] else 50,
                    "fat_g": 18 if mt in ["lunch", "dinner"] else 12,
                },
            )
            planned_meal_items.append(pmi)

    session.add_all(planned_meals)
    await session.flush()
    session.add_all(planned_meal_items)
    await session.flush()

    # 10. Create 14 Days of Nutrition Intake Logs
    nutrition_logs = []
    nutrition_log_items = []

    for d in range(14):
        log_date = today - timedelta(days=14 - d)
        for mt in ["breakfast", "lunch", "dinner"]:
            rec = catalogue_recipes[(d + len(mt)) % len(catalogue_recipes)]
            log_time = datetime(log_date.year, log_date.month, log_date.day, 12, 30, tzinfo=UTC)
            nl = NutritionLog(
                id=uuid.uuid4(),
                user_id=demo_user_id,
                consumed_at=log_time,
                meal_type=mt,
                source_type="recipe",
                notes="Synthetic intake record (AC-106)",
            )
            nutrition_logs.append(nl)

            nli = NutritionLogItem(
                id=uuid.uuid4(),
                nutrition_log_id=nl.id,
                recipe_id=rec.id,
                quantity=Decimal("1.0"),
                unit="serving",
                nutrient_snapshot={
                    "energy_kcal": 670,
                    "protein_g": 42.0,
                    "carbs_g": 78.0,
                    "fat_g": 19.0,
                },
            )
            nutrition_log_items.append(nli)

    session.add_all(nutrition_logs)
    await session.flush()
    session.add_all(nutrition_log_items)
    await session.commit()

    return {
        "sessions": len(workout_sessions),
        "sets": len(workout_sets),
        "meal_plans": 1,
        "planned_meals": len(planned_meals),
        "nutrition_logs": len(nutrition_logs),
    }


async def main() -> None:
    print(f"--- Creating Synthetic Demo Account: {DEMO_EMAIL} ---")
    async with async_session_factory() as session:
        stats = await create_demo_user(session, num_sessions=500, quick_mode=False)
        print("Demo account successfully initialized:")
        print(f"  Email:              {DEMO_EMAIL}")
        print(f"  Password:           {DEMO_PASS}")
        print(f"  Sessions Generated: {stats['sessions']}")
        print(f"  Sets Generated:     {stats['sets']}")
        print(f"  Planned Meals:      {stats['planned_meals']}")
        print(f"  Intake Logs:        {stats['nutrition_logs']}")
        print("Status: Synthetic dataset ready for UI demo and performance benchmarking.")


if __name__ == "__main__":
    asyncio.run(main())
