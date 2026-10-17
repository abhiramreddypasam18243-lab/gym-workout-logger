"""Data export and account deletion service (spec §6, FR-15, SEC1, S10, AC-88, AC-89)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from fastapi import HTTPException, Response, status
import jsonschema
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.nutrition import (
    MealPlan,
    NutritionGoal,
    NutritionLog,
    NutritionLogItem,
    PlannedMeal,
    PlannedMealItem,
)
from app.models.user import Session, User, UserCuisinePreference, UserFoodConstraint, UserProfile
from app.models.workout import (
    Exercise,
    RoutineExercise,
    WorkoutExercise,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSet,
)
from app.schemas.data_export import (
    CompleteUserDataExport,
    CuisinePreferenceExportData,
    CustomExerciseExportData,
    ExportMetadata,
    FoodConstraintExportData,
    MealPlanExportData,
    NutritionGoalExportData,
    NutritionLogExportData,
    NutritionLogItemExportData,
    PlannedMealExportData,
    PlannedMealItemExportData,
    ProfileExportData,
    RoutineExerciseExportData,
    RoutineExportData,
    UserExportData,
    WorkoutExerciseExportData,
    WorkoutSessionExportData,
    WorkoutSetExportData,
    get_export_json_schema,
)
from app.services.security import verify_password


class DataControlsService:
    """Handles GDPR/privacy data controls: complete JSON export and verified account deletion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_user_data(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Generate complete export of every record across every user-owned table (AC-88)."""
        # 1. User
        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

        # 2. Profile
        prof_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        prof = (await self.db.execute(prof_stmt)).scalar_one_or_none()
        profile_data = None
        display_name = prof.display_name if (prof and prof.display_name) else user.email.split("@")[0]

        user_data = UserExportData(
            id=str(user.id),
            email=user.email,
            display_name=display_name,
            created_at=user.created_at.isoformat() if user.created_at else datetime.now(UTC).isoformat(),
        )

        if prof:
            profile_data = ProfileExportData(
                user_id=str(prof.user_id),
                display_name=prof.display_name,
                birth_date=str(prof.birth_date) if prof.birth_date else None,
                height_cm=str(prof.height_cm) if prof.height_cm else None,
                body_weight_kg=str(prof.body_weight_kg) if prof.body_weight_kg else None,
                timezone=prof.timezone,
                units=prof.units,
                sex_for_estimate=prof.sex_for_estimate,
                adult_confirmed_at=prof.adult_confirmed_at.isoformat() if prof.adult_confirmed_at else None,
                needs_professional_guidance=prof.needs_professional_guidance,
                calories_hidden=prof.calories_hidden,
                nutrition_paused=prof.nutrition_paused,
                track_body_weight=prof.track_body_weight,
                weekly_session_target=prof.weekly_session_target,
                currency_code=prof.currency_code,
                goal=prof.goal,
                activity_level=prof.activity_level,
            )

        # 3. Food Constraints (Allergies, Diet Tags, Exclusions)
        cons_stmt = select(UserFoodConstraint).where(UserFoodConstraint.user_id == user_id)
        constraints = (await self.db.execute(cons_stmt)).scalars().all()
        food_constraints_data = [
            FoodConstraintExportData(
                id=str(c.id),
                constraint_type=c.constraint_type,
                constraint_value=c.constraint_value,
                is_hard_constraint=c.is_hard_constraint,
            )
            for c in constraints
        ]

        # 4. Cuisine Preferences
        cuis_stmt = select(UserCuisinePreference).where(UserCuisinePreference.user_id == user_id)
        cuisines = (await self.db.execute(cuis_stmt)).scalars().all()
        cuisine_preferences_data = [
            CuisinePreferenceExportData(
                id=str(cp.id),
                cuisine_code=cp.cuisine_code,
                preference_level=cp.preference_level,
            )
            for cp in cuisines
        ]

        # 5. Nutrition Goals
        goals_stmt = (
            select(NutritionGoal)
            .where(NutritionGoal.user_id == user_id)
            .order_by(NutritionGoal.created_at.asc())
        )
        goals = (await self.db.execute(goals_stmt)).scalars().all()
        nutrition_goals_data = [
            NutritionGoalExportData(
                id=str(g.id),
                effective_from=str(g.effective_from),
                calorie_target_kcal=g.calorie_target_kcal,
                protein_target_g=g.protein_target_g,
                carbs_target_g=g.carbs_target_g,
                fat_target_g=g.fat_target_g,
                rationale=g.rationale,
                created_at=g.created_at.isoformat() if g.created_at else datetime.now(UTC).isoformat(),
            )
            for g in goals
        ]

        # 6. Routines
        routines_stmt = (
            select(WorkoutRoutine)
            .where(WorkoutRoutine.user_id == user_id)
            .options(selectinload(WorkoutRoutine.exercises))
            .order_by(WorkoutRoutine.created_at.asc())
        )
        routines = (await self.db.execute(routines_stmt)).scalars().all()
        routines_data = []
        routine_exercises_count = 0
        for r in routines:
            re_list = []
            for rx in r.exercises:
                routine_exercises_count += 1
                re_list.append(
                    RoutineExerciseExportData(
                        exercise_id=str(rx.exercise_id),
                        order_index=rx.order_index,
                        target_sets=rx.target_sets,
                        rep_min=rx.rep_min,
                        rep_max=rx.rep_max,
                    )
                )
            routines_data.append(
                RoutineExportData(
                    id=str(r.id),
                    name=r.name,
                    description=r.description,
                    created_at=r.created_at.isoformat() if r.created_at else datetime.now(UTC).isoformat(),
                    exercises=re_list,
                )
            )

        # 7. Workout Sessions
        ws_stmt = (
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .options(
                selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
            )
            .order_by(WorkoutSession.started_at.asc())
        )
        sessions = (await self.db.execute(ws_stmt)).scalars().all()
        workout_sessions_data = []
        workout_exercises_count = 0
        workout_sets_count = 0
        for s in sessions:
            ex_list = []
            for we in s.exercises:
                workout_exercises_count += 1
                sets_list = []
                for ws in we.sets:
                    workout_sets_count += 1
                    sets_list.append(
                        WorkoutSetExportData(
                            id=str(ws.id),
                            set_number=ws.set_number,
                            reps=ws.reps,
                            load_kg=str(ws.load_kg),
                            rpe=str(ws.rpe) if ws.rpe is not None else None,
                            is_warmup=ws.is_warmup,
                            completed_at=ws.completed_at.isoformat() if ws.completed_at else None,
                        )
                    )
                ex_list.append(
                    WorkoutExerciseExportData(
                        id=str(we.id),
                        exercise_id=str(we.exercise_id),
                        order_index=we.order_index,
                        notes=we.notes,
                        sets=sets_list,
                    )
                )
            workout_sessions_data.append(
                WorkoutSessionExportData(
                    id=str(s.id),
                    routine_id=str(s.routine_id) if s.routine_id else None,
                    started_at=s.started_at.isoformat() if s.started_at else datetime.now(UTC).isoformat(),
                    completed_at=s.completed_at.isoformat() if s.completed_at else None,
                    notes=s.notes,
                    exercises=ex_list,
                )
            )

        # 8. Custom Exercises (owner_user_id == user_id)
        cust_ex_stmt = (
            select(Exercise)
            .where(Exercise.owner_user_id == user_id)
            .order_by(Exercise.name.asc())
        )
        cust_exercises = (await self.db.execute(cust_ex_stmt)).scalars().all()
        custom_exercises_data = [
            CustomExerciseExportData(
                id=str(ce.id),
                name=ce.name,
                primary_muscle=ce.primary_muscle,
                equipment=ce.equipment,
                movement_pattern=ce.movement_pattern or "",
                instructions=ce.instructions,
            )
            for ce in cust_exercises
        ]

        # 9. Meal Plans
        plans_stmt = (
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .options(
                selectinload(MealPlan.meals).selectinload(PlannedMeal.items)
            )
            .order_by(MealPlan.created_at.asc())
        )
        plans = (await self.db.execute(plans_stmt)).scalars().all()
        meal_plans_data = []
        planned_meals_count = 0
        planned_meal_items_count = 0
        for p in plans:
            m_list = []
            for pm in p.meals:
                planned_meals_count += 1
                items_list = []
                for pmi in pm.items:
                    planned_meal_items_count += 1
                    items_list.append(
                        PlannedMealItemExportData(
                            id=str(pmi.id),
                            food_id=str(pmi.food_id) if pmi.food_id else None,
                            recipe_id=str(pmi.recipe_id) if pmi.recipe_id else None,
                            quantity=str(pmi.quantity),
                            unit=pmi.unit,
                            nutrient_snapshot=pmi.nutrient_snapshot,
                        )
                    )
                m_list.append(
                    PlannedMealExportData(
                        id=str(pm.id),
                        plan_date=str(pm.plan_date),
                        meal_type=pm.meal_type,
                        title=pm.title,
                        recipe_id=str(pm.recipe_id) if pm.recipe_id else None,
                        servings=str(pm.servings),
                        sort_order=pm.sort_order,
                        items=items_list,
                    )
                )
            meal_plans_data.append(
                MealPlanExportData(
                    id=str(p.id),
                    start_date=str(p.start_date),
                    end_date=str(p.end_date),
                    status=p.status,
                    created_at=p.created_at.isoformat() if p.created_at else datetime.now(UTC).isoformat(),
                    planned_meals=m_list,
                )
            )

        # 10. Nutrition Logs
        nlogs_stmt = (
            select(NutritionLog)
            .where(NutritionLog.user_id == user_id)
            .options(selectinload(NutritionLog.items))
            .order_by(NutritionLog.consumed_at.asc())
        )
        nlogs = (await self.db.execute(nlogs_stmt)).scalars().all()
        nutrition_logs_data = []
        nutrition_log_items_count = 0
        for nl in nlogs:
            it_list = []
            for nli in nl.items:
                nutrition_log_items_count += 1
                it_list.append(
                    NutritionLogItemExportData(
                        id=str(nli.id),
                        food_id=str(nli.food_id) if nli.food_id else None,
                        recipe_id=str(nli.recipe_id) if nli.recipe_id else None,
                        quantity=str(nli.quantity),
                        unit=nli.unit,
                        nutrient_snapshot=nli.nutrient_snapshot,
                    )
                )
            nutrition_logs_data.append(
                NutritionLogExportData(
                    id=str(nl.id),
                    consumed_at=nl.consumed_at.isoformat() if nl.consumed_at else datetime.now(UTC).isoformat(),
                    meal_type=nl.meal_type,
                    source_type=nl.source_type,
                    notes=nl.notes,
                    items=it_list,
                )
            )

        record_counts = {
            "users": 1,
            "user_profiles": 1 if profile_data else 0,
            "user_food_constraints": len(food_constraints_data),
            "user_cuisine_preferences": len(cuisine_preferences_data),
            "nutrition_goals": len(nutrition_goals_data),
            "workout_routines": len(routines_data),
            "routine_exercises": routine_exercises_count,
            "workout_sessions": len(workout_sessions_data),
            "workout_exercises": workout_exercises_count,
            "workout_sets": workout_sets_count,
            "custom_exercises": len(custom_exercises_data),
            "meal_plans": len(meal_plans_data),
            "planned_meals": planned_meals_count,
            "planned_meal_items": planned_meal_items_count,
            "nutrition_logs": len(nutrition_logs_data),
            "nutrition_log_items": nutrition_log_items_count,
        }

        export_model = CompleteUserDataExport(
            metadata=ExportMetadata(
                export_version="1.0",
                user_id=str(user_id),
                exported_at=datetime.now(UTC).isoformat(),
                record_counts=record_counts,
            ),
            user=user_data,
            profile=profile_data,
            food_constraints=food_constraints_data,
            cuisine_preferences=cuisine_preferences_data,
            nutrition_goals=nutrition_goals_data,
            routines=routines_data,
            workout_sessions=workout_sessions_data,
            custom_exercises=custom_exercises_data,
            meal_plans=meal_plans_data,
            nutrition_logs=nutrition_logs_data,
        )

        export_dict = export_model.model_dump()

        # Validate against published JSON schema
        schema = get_export_json_schema()
        jsonschema.validate(instance=export_dict, schema=schema)

        return export_dict

    async def delete_user_account(
        self,
        user_id: uuid.UUID,
        password: str,
        response: Response,
    ) -> dict[str, str]:
        """Delete user account and all personal data, requiring password verification (AC-89)."""
        # 1. Fetch user and verify password
        user_stmt = select(User).where(User.id == user_id)
        user = (await self.db.execute(user_stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")

        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_password", "message": "Incorrect password for account deletion"},
            )

        # 2. Delete Nutrition Logs and items
        nlogs_q = select(NutritionLog.id).where(NutritionLog.user_id == user_id)
        nlogs_ids = (await self.db.execute(nlogs_q)).scalars().all()
        if nlogs_ids:
            await self.db.execute(
                delete(NutritionLogItem).where(NutritionLogItem.nutrition_log_id.in_(nlogs_ids))
            )
            await self.db.execute(delete(NutritionLog).where(NutritionLog.user_id == user_id))

        # 3. Delete Meal Plans, planned meals, planned meal items
        plans_q = select(MealPlan.id).where(MealPlan.user_id == user_id)
        plans_ids = (await self.db.execute(plans_q)).scalars().all()
        if plans_ids:
            meals_q = select(PlannedMeal.id).where(PlannedMeal.meal_plan_id.in_(plans_ids))
            meals_ids = (await self.db.execute(meals_q)).scalars().all()
            if meals_ids:
                await self.db.execute(
                    delete(PlannedMealItem).where(PlannedMealItem.planned_meal_id.in_(meals_ids))
                )
                await self.db.execute(delete(PlannedMeal).where(PlannedMeal.meal_plan_id.in_(plans_ids)))
            await self.db.execute(delete(MealPlan).where(MealPlan.user_id == user_id))

        # 4. Delete Workout Sessions, exercises, sets
        ws_q = select(WorkoutSession.id).where(WorkoutSession.user_id == user_id)
        ws_ids = (await self.db.execute(ws_q)).scalars().all()
        if ws_ids:
            we_q = select(WorkoutExercise.id).where(WorkoutExercise.session_id.in_(ws_ids))
            we_ids = (await self.db.execute(we_q)).scalars().all()
            if we_ids:
                await self.db.execute(
                    delete(WorkoutSet).where(WorkoutSet.workout_exercise_id.in_(we_ids))
                )
                await self.db.execute(
                    delete(WorkoutExercise).where(WorkoutExercise.session_id.in_(ws_ids))
                )
            await self.db.execute(delete(WorkoutSession).where(WorkoutSession.user_id == user_id))

        # 5. Delete Routines and routine exercises
        r_q = select(WorkoutRoutine.id).where(WorkoutRoutine.user_id == user_id)
        r_ids = (await self.db.execute(r_q)).scalars().all()
        if r_ids:
            await self.db.execute(
                delete(RoutineExercise).where(RoutineExercise.routine_id.in_(r_ids))
            )
            await self.db.execute(delete(WorkoutRoutine).where(WorkoutRoutine.user_id == user_id))

        # 6. Delete Custom Exercises (owner_user_id == user_id)
        await self.db.execute(delete(Exercise).where(Exercise.owner_user_id == user_id))

        # 7. Delete Nutrition Goals and Constraints
        await self.db.execute(delete(NutritionGoal).where(NutritionGoal.user_id == user_id))
        await self.db.execute(delete(UserFoodConstraint).where(UserFoodConstraint.user_id == user_id))
        await self.db.execute(delete(UserCuisinePreference).where(UserCuisinePreference.user_id == user_id))

        # 8. Delete UserProfile
        await self.db.execute(delete(UserProfile).where(UserProfile.user_id == user_id))

        # 9. Revoke & Delete Sessions
        await self.db.execute(delete(Session).where(Session.user_id == user_id))

        # 10. Delete User Record
        await self.db.execute(delete(User).where(User.id == user_id))

        await self.db.commit()

        # 12. Clear cookies
        response.delete_cookie(key="session_id", path="/")
        response.delete_cookie(key="csrf_token", path="/")

        return {"message": "Account and all personal data deleted successfully"}
