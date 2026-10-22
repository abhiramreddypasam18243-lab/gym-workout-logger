"""Workout progress (D-33, D-34): overload hints (AC-123), top-set trend (AC-124), weekly sets per muscle (AC-125)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.domain.progression import count_working_sets_by_muscle, suggest_next_load
from app.domain.strength import StrengthSetInput
from app.models.workout import Exercise
from app.seed.loader import run_seed
from tests.test_acceptance_gaps import make_user, session_factory  # noqa: F401


def _sets(*pairs: tuple[str, int], warmups: tuple[tuple[str, int], ...] = ()) -> list[StrengthSetInput]:
    out = [StrengthSetInput(load_kg=Decimal(w), reps=r, is_warmup=True, set_number=i) for i, (w, r) in enumerate(warmups)]
    out += [
        StrengthSetInput(load_kg=Decimal(w), reps=r, set_number=len(warmups) + i + 1) for i, (w, r) in enumerate(pairs)
    ]
    return out


# ---------------------------------------------------------------------------
# AC-123: the double-progression rule (pure domain)
# ---------------------------------------------------------------------------


def test_ac_123_every_set_at_top_of_range_adds_one_step():
    hint = suggest_next_load(_sets(("60", 12), ("60", 12), ("60", 13)), 8, 12, Decimal("2.5"))
    assert hint is not None
    assert hint.action == "increase_load"
    assert hint.top_load_kg == Decimal("60")
    assert hint.suggested_load_kg == Decimal("62.5")
    assert hint.reps_at_top_load == (12, 12, 13)


def test_ac_123_short_of_top_keeps_load():
    hint = suggest_next_load(_sets(("60", 12), ("60", 11), ("60", 10)), 8, 12, Decimal("2.5"))
    assert hint is not None and hint.action == "keep_load"
    assert hint.suggested_load_kg == Decimal("60")
    assert "add reps" in hint.reason


def test_ac_123_below_bottom_keeps_load_and_never_lowers_it():
    hint = suggest_next_load(_sets(("60", 9), ("60", 7)), 8, 12, Decimal("2.5"))
    assert hint is not None and hint.action == "keep_load"
    assert hint.suggested_load_kg == Decimal("60")
    assert "below 8" in hint.reason


def test_ac_123_only_working_sets_at_the_heaviest_load_count():
    # Warm-ups are ignored; the 70 kg set decides, not the lighter 12-rep sets
    hint = suggest_next_load(
        _sets(("60", 12), ("60", 12), ("70", 6), warmups=(("40", 12),)), 8, 12, Decimal("2.5")
    )
    assert hint is not None
    assert hint.top_load_kg == Decimal("70") and hint.reps_at_top_load == (6,)
    assert hint.action == "keep_load"


def test_ac_123_no_working_sets_or_bad_range():
    assert suggest_next_load(_sets(warmups=(("40", 10),)), 8, 12, Decimal("2.5")) is None
    with pytest.raises(ValueError):
        suggest_next_load(_sets(("60", 10)), 12, 8, Decimal("2.5"))


def test_ac_125_count_working_sets_by_muscle():
    pairs = [("Quads", False), ("quads", False), ("quads", True), ("chest", False)]
    assert count_working_sets_by_muscle(pairs) == {"quads": 2, "chest": 1}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


async def _exercise_ids(factory) -> dict[str, str]:
    async with factory() as db:
        await run_seed(db)
        rows = (await db.execute(select(Exercise).where(Exercise.owner_user_id.is_(None)))).scalars()
        return {e.name: str(e.id) for e in rows}


async def _log(client, started: datetime, exercises: list[tuple[str, list[tuple[str, int, bool]]]]) -> None:
    body = {
        "started_at": started.isoformat(),
        "completed_at": (started + timedelta(minutes=1)).isoformat(),
        "exercises": [
            {
                "exercise_id": ex_id,
                "order_index": i,
                "sets": [
                    {
                        "set_number": n + 1,
                        "load_kg": load,
                        "reps": reps,
                        "is_warmup": warm,
                        "completed_at": (started + timedelta(seconds=30)).isoformat(),
                    }
                    for n, (load, reps, warm) in enumerate(sets)
                ],
            }
            for i, (ex_id, sets) in enumerate(exercises)
        ],
    }
    res = await client.post("/api/workouts", json=body)
    assert res.status_code == 201, res.text


@pytest.mark.asyncio
async def test_ac_123_next_load_api_uses_muscle_steps_and_units(session_factory):  # noqa: F811
    ids = await _exercise_ids(session_factory)
    squat, bench = ids["Barbell Back Squat"], ids["Barbell Bench Press"]
    _, client = await make_user(session_factory, "progress@example.com")
    _, lb_client = await make_user(session_factory, "pounds@example.com")
    now = datetime.now(UTC) - timedelta(minutes=2)
    async with client, lb_client:
        assert (await client.get(f"/api/analytics/next-load/{squat}")).json()["action"] == "no_history"

        # An older session must not decide the hint; the most recent one does
        await _log(client, now - timedelta(days=3), [(squat, [("100", 5, False)])])
        await _log(client, now, [(squat, [("60", 10, True), ("100", 12, False), ("100", 12, False), ("100", 12, False)])])
        hint = (await client.get(f"/api/analytics/next-load/{squat}")).json()
        assert hint["action"] == "increase_load"
        assert (hint["top_load"], hint["suggested_load"], hint["unit"]) == ("100.0", "105.0", "kg")  # lower body: +5 kg
        assert (hint["rep_min"], hint["rep_max"]) == (8, 12)
        assert hint["reps_at_top_load"] == [12, 12, 12]

        # With a routine's 12-15 range, 12 reps is the bottom of the range, so keep the load
        assert (await client.get(f"/api/analytics/next-load/{squat}", params={"rep_min": 12, "rep_max": 15})).json()[
            "action"
        ] == "keep_load"
        bad = await client.get(f"/api/analytics/next-load/{squat}", params={"rep_min": 10, "rep_max": 6})
        assert bad.status_code == 422

        # Upper body, lb user: 100 lb is 45.359237 kg; step +5 lb
        assert (await lb_client.patch("/api/profile", json={"units": "lb"})).status_code == 200
        await _log(lb_client, now, [(bench, [("45.36", 12, False), ("45.36", 12, False)])])
        lb_hint = (await lb_client.get(f"/api/analytics/next-load/{bench}")).json()
        assert (lb_hint["top_load"], lb_hint["suggested_load"], lb_hint["unit"]) == ("100.0", "105.0", "lb")

        # Unknown exercise: 404
        missing = await client.get("/api/analytics/next-load/00000000-0000-0000-0000-000000000000")
        assert missing.status_code == 404


@pytest.mark.asyncio
async def test_ac_124_trend_reports_top_set_alongside_best_e1rm(session_factory):  # noqa: F811
    ids = await _exercise_ids(session_factory)
    squat = ids["Barbell Back Squat"]
    _, client = await make_user(session_factory, "topset@example.com")
    async with client:
        # e1RM: 100 x (1 + 5/30) = 116.7; 90 x (1 + 12/30) = 126.0, so the 90 kg set is the best e1RM,
        # while the heaviest set of the day is 100 kg
        await _log(client, datetime.now(UTC) - timedelta(minutes=2), [(squat, [("100", 5, False), ("90", 12, False)])])
        trend = (await client.get("/api/analytics/strength", params={"exercise_id": squat})).json()
    assert len(trend) == 1
    point = trend[0]
    assert (point["e1rm"], point["load"], point["reps"]) == ("126.0", "90.0", 12)
    assert (point["top_set_load"], point["top_set_reps"]) == ("100.0", 5)


@pytest.mark.asyncio
async def test_ac_125_weekly_sets_per_muscle_against_targets(session_factory):  # noqa: F811
    ids = await _exercise_ids(session_factory)
    squat, bench = ids["Barbell Back Squat"], ids["Barbell Bench Press"]
    _, client = await make_user(session_factory, "volume@example.com")
    _, other = await make_user(session_factory, "volume.other@example.com")
    now = datetime.now(UTC) - timedelta(minutes=2)
    async with client, other:
        await _log(
            client,
            now,
            [
                (squat, [("60", 10, True), ("100", 8, False), ("100", 8, False), ("100", 8, False)]),
                (bench, [("80", 8, False), ("80", 8, False)]),
            ],
        )
        await _log(client, now - timedelta(days=8), [(bench, [("80", 8, False)] * 5)])  # last week: not counted
        await _log(other, now, [(bench, [("80", 8, False)] * 4)])  # someone else's sets: not counted

        for bad in ({"chest": 0}, {"chest": 41}, {"": 5}):
            assert (await client.put("/api/analytics/weekly-volume/targets", json={"targets": bad})).status_code == 422
        saved = await client.put("/api/analytics/weekly-volume/targets", json={"targets": {"Quads": 3, "chest": 10, "back": 12}})
        assert saved.status_code == 200, saved.text
        assert saved.json()["targets"] == {"quads": 3, "chest": 10, "back": 12}

        week = (await client.get("/api/analytics/weekly-volume")).json()
        rows = {m["muscle"]: m for m in week["muscles"]}
        assert (rows["quads"]["sets"], rows["quads"]["target"], rows["quads"]["met"]) == (3, 3, True)
        assert (rows["chest"]["sets"], rows["chest"]["target"], rows["chest"]["met"]) == (2, 10, False)
        assert (rows["back"]["sets"], rows["back"]["met"]) == (0, False)
        monday = datetime.now(UTC).date() - timedelta(days=datetime.now(UTC).weekday())
        assert week["week_start"] == monday.isoformat()

        export = (await client.get("/api/me/export")).json()
        assert export["muscle_set_targets"] == {"quads": 3, "chest": 10, "back": 12}

        cleared = await client.put("/api/analytics/weekly-volume/targets", json={"targets": {}})
        assert cleared.json()["targets"] == {}
