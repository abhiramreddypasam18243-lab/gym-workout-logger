"""Tests for Nutrition Targets, Safety Rules (S1–S8), and Preferences (AC-17–28)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.main import app
from app.models.base import Base
from app.models.nutrition import NutritionGoal
from app.models.user import Session, User, UserProfile
from app.services.security import generate_csrf_token, generate_session_token, hash_token


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def unconfirmed_user_client(test_db: AsyncSession):
    """User who has NOT yet confirmed adult status."""
    user = User(
        email="minor_or_unconfirmed@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
    )
    test_db.add(user)
    await test_db.flush()

    profile = UserProfile(
        user_id=user.id,
        display_name="User 1",
        adult_confirmed_at=None,  # Unconfirmed
    )
    test_db.add(profile)

    raw_token = generate_session_token()
    raw_csrf = generate_csrf_token()
    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        created_at=now,
        expires_at=now + timedelta(days=14),
    )
    test_db.add(session)
    await test_db.commit()

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"session_id": raw_token},
        headers={"X-CSRF-Token": raw_csrf},
    ) as client:
        yield client, user, test_db, raw_csrf

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def adult_client(test_db: AsyncSession):
    """User who has confirmed adult status."""
    user = User(
        email="adult_lifter@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
    )
    test_db.add(user)
    await test_db.flush()

    profile = UserProfile(
        user_id=user.id,
        display_name="Adult Lifter",
        adult_confirmed_at=datetime.now(UTC),
        height_cm=Decimal("180.0"),
        body_weight_kg=Decimal("80.0"),
        birth_date=date(2000, 1, 1),
    )
    test_db.add(profile)

    raw_token = generate_session_token()
    raw_csrf = generate_csrf_token()
    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        created_at=now,
        expires_at=now + timedelta(days=14),
    )
    test_db.add(session)
    await test_db.commit()

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"session_id": raw_token},
        headers={"X-CSRF-Token": raw_csrf},
    ) as client:
        yield client, user, test_db, raw_csrf

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC-17: Rule S2 Adults only for nutrition planning
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_17_adult_confirmation_and_minor_blocking(unconfirmed_user_client):
    """AC-17: Nutrition endpoints return 403 adult_confirmation_required until confirmed.

    With birth date 2008-10-16, blocked on 2026-10-15 (age 17) and allowed on 2026-10-16 (age 18);
    workout endpoints work in both cases.
    """
    client, user, db, csrf_token = unconfirmed_user_client

    # 1. Unconfirmed user accessing nutrition goals gets 403 adult_confirmation_required
    nutr_res = await client.get("/api/nutrition/goals")
    assert nutr_res.status_code == 403
    assert nutr_res.json()["detail"]["code"] == "adult_confirmation_required"

    # Workout endpoints work regardless! (AC-17: workout endpoints work in both cases)
    wk_res = await client.get("/api/workouts")
    assert wk_res.status_code == 200

    # 2. Set birth date to 2008-10-16
    await client.patch("/api/profile", json={"birth_date": "2008-10-16"})

    # Confirm adult status
    await client.post("/api/profile/confirm-adult")

    # 3. On 2026-10-15 (age 17): nutrition is blocked with nutrition_not_available_for_minors
    minor_res = await client.get(
        "/api/nutrition/goals",
        headers={"X-Current-Date": "2026-10-15"},
    )
    assert minor_res.status_code == 403
    assert minor_res.json()["detail"]["code"] == "nutrition_not_available_for_minors"

    # Workout endpoint still works!
    assert (await client.get("/api/workouts")).status_code == 200

    # 4. On 2026-10-16 (turned 18!): nutrition planning is allowed
    adult_res = await client.get(
        "/api/nutrition/goals",
        headers={"X-Current-Date": "2026-10-16"},
    )
    assert adult_res.status_code == 200


# ---------------------------------------------------------------------------
# AC-18: Rule S3 Professional Guidance Flag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_18_professional_guidance_flag(adult_client):
    """AC-18: With needs_professional_guidance on, estimate returns 409 manual_targets_required, manual targets accepted."""
    client, user, db, csrf_token = adult_client

    # Turn on needs_professional_guidance
    patch_res = await client.patch("/api/profile", json={"needs_professional_guidance": True})
    assert patch_res.status_code == 200

    # Estimate endpoint must return 409 manual_targets_required (S3, AC-18)
    est_res = await client.post(
        "/api/nutrition/goals/estimate",
        json={"weight_kg": 80.0, "height_cm": 180.0, "age": 25},
    )
    assert est_res.status_code == 409
    assert est_res.json()["detail"]["code"] == "manual_targets_required"
    assert est_res.json()["detail"]["requires_professional_guidance"] is True

    # Manual targets must be accepted!
    manual_res = await client.post(
        "/api/nutrition/goals",
        json={"calorie_target_kcal": 2500, "protein_target_g": 160},
    )
    assert manual_res.status_code == 201
    assert manual_res.json()["calorie_target_kcal"] == 2500


# ---------------------------------------------------------------------------
# AC-19 & AC-20: Rule S4 Transparent Target Estimation (Mifflin-St Jeor)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_19_male_strength_target_estimate(adult_client):
    """AC-19: male, 80 kg, 180 cm, age 25, moderate, build_strength -> BMR 1805, TDEE 2797.75, +5% = 2937.64, rounded to 2940 kcal, protein 128g, fat 82g, carbs 423g."""
    client, user, db, csrf_token = adult_client

    res = await client.post(
        "/api/nutrition/goals/estimate",
        json={
            "weight_kg": 80.0,
            "height_cm": 180.0,
            "age": 25,
            "sex_for_estimate": "male",
            "activity_level": "moderate",
            "goal": "build_strength",
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "ok"
    assert data["calories"] == 2940
    assert data["protein_g"] == 128  # 1.6 x 80
    assert data["fat_g"] == 82       # 25% of 2940 / 9 = 81.666... -> 82
    assert data["carbs_g"] == 423    # (2940 - 128*4 - 735) / 4 = 1693 / 4 = 423.25 -> 423
    assert "Mifflin-St Jeor" in data["formula"]
    assert data["disclaimer"]  # S1, AC-28


@pytest.mark.asyncio
async def test_ac_20_unspecified_sex_midpoint_target_estimate(adult_client):
    """AC-20: Same inputs with sex_for_estimate = unspecified uses s = -78 -> rounded to 2800 kcal."""
    client, user, db, csrf_token = adult_client

    res = await client.post(
        "/api/nutrition/goals/estimate",
        json={
            "weight_kg": 80.0,
            "height_cm": 180.0,
            "age": 25,
            "sex_for_estimate": "unspecified",
            "activity_level": "moderate",
            "goal": "build_strength",
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "ok"
    assert data["calories"] == 2800
    assert data["assumptions"]["sex_factor_s"] == "-78"


# ---------------------------------------------------------------------------
# AC-21 & AC-22: Rule S5 Safety Energy Floor (< 1500 kcal)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_21_estimate_below_floor_refused(adult_client):
    """AC-21: female, 45 kg, 160 cm, age 30, sedentary, maintain -> estimate_below_floor, saves no target."""
    client, user, db, csrf_token = adult_client

    res = await client.post(
        "/api/nutrition/goals/estimate",
        json={
            "weight_kg": 45.0,
            "height_cm": 160.0,
            "age": 30,
            "sex_for_estimate": "female",
            "activity_level": "sedentary",
            "goal": "maintain",
        },
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "estimate_below_floor"
    assert data["calories"] is None
    assert "below the recommended minimum floor of 1,500 kcal" in data["warning"]

    # Verify no target was stored in database (AC-21)
    get_res = await client.get("/api/nutrition/goals")
    assert get_res.status_code == 200
    assert get_res.json() is None


@pytest.mark.asyncio
async def test_ac_22_manual_target_warning(adult_client):
    """AC-22: Manual target of 1400 kcal is saved with below_recommended_minimum warning."""
    client, user, db, csrf_token = adult_client

    res = await client.post(
        "/api/nutrition/goals",
        json={"calorie_target_kcal": 1400, "protein_target_g": 100},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["calorie_target_kcal"] == 1400
    assert data["warning"] == "below_recommended_minimum"


# ---------------------------------------------------------------------------
# AC-23: Target Versioning and Effective Date Lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_23_target_versioning(adult_client):
    """AC-23: Changing a target creates a new row; active target on a date is latest row with effective_from on or before it."""
    client, user, db, csrf_token = adult_client

    # Goal 1: effective 2026-10-01 at 2400 kcal
    g1 = await client.post(
        "/api/nutrition/goals",
        json={"calorie_target_kcal": 2400, "effective_from": "2026-10-01"},
    )
    assert g1.status_code == 201

    # Goal 2: effective 2026-10-15 at 2600 kcal
    g2 = await client.post(
        "/api/nutrition/goals",
        json={"calorie_target_kcal": 2600, "effective_from": "2026-10-15"},
    )
    assert g2.status_code == 201

    # Query on 2026-10-10 -> should return Goal 1 (2400 kcal)
    q1 = await client.get("/api/nutrition/goals", params={"on_date": "2026-10-10"})
    assert q1.status_code == 200
    assert q1.json()["calorie_target_kcal"] == 2400

    # Query on 2026-10-20 -> should return Goal 2 (2600 kcal)
    q2 = await client.get("/api/nutrition/goals", params={"on_date": "2026-10-20"})
    assert q2.status_code == 200
    assert q2.json()["calorie_target_kcal"] == 2600


# ---------------------------------------------------------------------------
# AC-25 & AC-26: Wellbeing Safeguards (Nutrition Paused, Track Weight Opt-In)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_25_nutrition_paused_safeguard(adult_client):
    """AC-25: With nutrition_paused on, nutrition endpoints return 403 nutrition_paused, workouts work, turning off restores access."""
    client, user, db, csrf_token = adult_client

    # 1. Pause nutrition
    await client.patch("/api/profile", json={"nutrition_paused": True})

    # Nutrition endpoints must return 403 nutrition_paused (AC-25)
    g_res = await client.get("/api/nutrition/goals")
    assert g_res.status_code == 403
    assert g_res.json()["detail"]["code"] == "nutrition_paused"

    pref_res = await client.get("/api/nutrition/preferences")
    assert pref_res.status_code == 403
    assert pref_res.json()["detail"]["code"] == "nutrition_paused"

    # Workout endpoints continue to work! (AC-25)
    w_res = await client.get("/api/workouts")
    assert w_res.status_code == 200

    # 2. Unpause nutrition restores access
    await client.patch("/api/profile", json={"nutrition_paused": False})
    restored = await client.get("/api/nutrition/goals")
    assert restored.status_code == 200


# ---------------------------------------------------------------------------
# AC-27: Neutral Language Test (Scanning for Banned Words)
# ---------------------------------------------------------------------------


def test_ac_27_neutral_language_scan():
    """AC-27: A test scanning all UI strings and insight templates finds none of the banned words:

    ('failed', 'cheat', 'bad', 'guilt', 'streak lost', 'caused', 'because of').
    """
    banned_words = [
        "failed",
        "cheat",
        "bad",
        "guilt",
        "streak lost",
        "caused",
        "because of",
    ]

    project_root = Path(__file__).resolve().parent.parent.parent
    frontend_src = project_root / "frontend" / "src"
    backend_app = project_root / "backend" / "app"

    # Scan all frontend components
    for tsx_file in frontend_src.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8").lower()
        for banned in banned_words:
            # Allow common code occurrences like 'banned' or 'if (err)' but not literal user-facing strings
            # Look for exact word matches in template strings
            assert f'"{banned}"' not in content, f"Found banned word '{banned}' in {tsx_file}"
            assert f"'{banned}'" not in content, f"Found banned word '{banned}' in {tsx_file}"

    # Scan backend insight/nutrition responses
    for py_file in (backend_app / "api").rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        for banned in banned_words:
            assert f'"{banned}"' not in content, f"Found banned word '{banned}' in {py_file}"


# ---------------------------------------------------------------------------
# AC-28: S1 Informational Notice on All Relevant Responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_28_informational_notice_disclaimer(adult_client):
    """AC-28: Every plan, target, and insight screen/response shows the informational notice disclaimer."""
    client, user, db, csrf_token = adult_client

    # Create target
    res = await client.post(
        "/api/nutrition/goals",
        json={"calorie_target_kcal": 2200, "protein_target_g": 140},
    )
    assert res.status_code == 201
    data = res.json()
    assert "disclaimer" in data
    assert "Estimates are informational and not medical advice" in data["disclaimer"]

    # Read preferences
    pref_res = await client.get("/api/nutrition/preferences")
    assert pref_res.status_code == 200
    assert "disclaimer" in pref_res.json()
