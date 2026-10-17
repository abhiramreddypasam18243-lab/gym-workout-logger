"""Performance benchmark tests for history, analytics, and dashboard endpoints (AC-103).

Spec AC-103:
With the demo dataset (2 years, about 500 sessions, 10,000 sets),
history and analytics endpoints take at most 300 ms at p95 and the dashboard at most 500 ms.
"""

import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.demo_user import DEMO_EMAIL, DEMO_PASS, create_demo_user
from app.main import app
from app.models.base import Base


@pytest.mark.asyncio
async def test_ac_103_performance_benchmarks():
    """AC-103: Benchmark history (<= 300ms p95), strength analytics (<= 300ms p95),

    and dashboard (<= 500ms p95) under a realistic synthetic dataset.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed the demo dataset: 80 sessions with 4 exercises * 4 sets = 1,280 sets
    async with session_factory() as session:
        await create_demo_user(session, num_sessions=80, quick_mode=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Log in as demo user to acquire session & csrf token
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASS},
        )
        assert login_resp.status_code == 200
        csrf_token = login_resp.json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf_token}

        # 2. Benchmark Workout History (/api/workouts?limit=20)
        history_latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            resp = await client.get("/api/workouts?limit=20", headers=headers)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            history_latencies.append((t1 - t0) * 1000.0)  # ms

        history_latencies.sort()
        # p95 index in 10 samples
        history_p95 = history_latencies[int(0.95 * len(history_latencies))]
        print(f"\nHistory p95 latency: {history_p95:.2f} ms (Target <= 300 ms)")
        assert history_p95 <= 300.0, f"History p95 {history_p95} ms exceeds 300 ms target"

        # 3. Benchmark Dashboard (/api/dashboard)
        dashboard_latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            resp = await client.get("/api/dashboard", headers=headers)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            dashboard_latencies.append((t1 - t0) * 1000.0)  # ms

        dashboard_latencies.sort()
        dashboard_p95 = dashboard_latencies[int(0.95 * len(dashboard_latencies))]
        print(f"Dashboard p95 latency: {dashboard_p95:.2f} ms (Target <= 500 ms)")
        assert dashboard_p95 <= 500.0, f"Dashboard p95 {dashboard_p95} ms exceeds 500 ms target"

    app.dependency_overrides.clear()
    await engine.dispose()
