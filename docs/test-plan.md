# Test Plan

Maps every acceptance criterion to a test file/method or manual check.

| AC | Category | Test Location | Type | Status |
| --- | --- | --- | --- | --- |
| AC-01 | Security | `tests/test_auth.py::test_ac_01_*` | API | ✅ Step 3 |
| AC-02 | Security | `tests/test_auth.py::test_ac_02_*` | API | ✅ Step 3 |
| AC-03 | Security | `tests/test_auth.py::test_ac_03_*` | API | ✅ Step 3 |
| AC-04 | Security | `tests/test_auth.py::test_ac_04_*` | API | ✅ Step 3 |
| AC-05 | Security | `tests/test_auth.py::test_ac_05_*` | API | ✅ Step 3 |
| AC-06 | Security | `tests/test_auth.py::test_ac_06_*` | API | ✅ Step 3 |
| AC-07 | Security | `tests/test_auth.py::test_ac_07_*` | API | ✅ Step 3 |
| AC-08 | Security | `tests/test_ownership.py::test_ac_08_*` | API | ✅ Step 3 |
| AC-09 | Security | `tests/test_auth.py::test_ac_09_*` | API | ✅ Step 3 |
| AC-10 | Security | `tests/test_auth.py::test_ac_10_*` | API | ✅ Step 3 |
| AC-11 | Security | `tests/test_auth.py::test_ac_11_*` | API | ✅ Step 3 |
| AC-12 | Security | `tests/test_secrets.py::test_ac_12_*` | CI | ✅ Step 3 |
| AC-13 | Security | `tests/test_auth.py::test_ac_13_*` | API | ✅ Step 3 |
| AC-14 | Security | Manual: `pip-audit` + `npm audit` | CI | ⬜ Step 12 |
| AC-15 | Profile | `tests/test_profile.py::test_ac_15_*` | API | ✅ Step 3 |
| AC-16 | Units | `tests/test_domain_units.py::test_ac_16_*` | Unit | ✅ Step 2 |
| AC-17 | Safety | `tests/test_safety.py::test_ac_17_*` | API | ✅ Step 7 |
| AC-18 | Safety | `tests/test_safety.py::test_ac_18_*` | API | ✅ Step 7 |
| AC-19 | Targets | `tests/test_domain_targets.py::test_ac_19_*` | Unit | ✅ Step 2 |
| AC-20 | Targets | `tests/test_domain_targets.py::test_ac_20_*` | Unit | ✅ Step 2 |
| AC-21 | Targets | `tests/test_domain_targets.py::test_ac_21_*` | Unit | ✅ Step 2 |
| AC-22 | Safety | `tests/test_safety.py::test_ac_22_*` | API | ✅ Step 7 |
| AC-23 | Targets | `tests/test_safety.py::test_ac_23_*` | API | ✅ Step 7 |
| AC-24–28 | Safety | `tests/test_safety.py` | API+UI | ✅ Step 7 |
| AC-29–30 | Exercises | `tests/test_catalogue.py` | API | ✅ Step 4, 5 |
| AC-31–34 | Workouts | `tests/test_workouts.py` | API | ✅ Step 5 |
| AC-35 | Routines | `tests/test_workouts.py` | API | ✅ Step 5 |
| AC-36–38 | Workouts | `tests/test_workouts.py` | API | ✅ Step 5 |
| AC-39–41, 43 | Strength | `tests/test_domain_strength.py` | Unit | ✅ Step 2 |
| AC-42, 44 | Strength | `tests/test_strength_service.py` | API | ✅ Step 6 |
| AC-45–47 | Nutrients | `tests/test_domain_nutrients.py` | Unit | ✅ Step 2 |
| AC-48–55 | Catalogue | `tests/test_catalogue.py` | DB+API | ✅ Step 4 |
| AC-63–64 | Scoring | `tests/test_domain_scoring.py` | Unit | ✅ Step 2 |
| AC-56–62, 65–72 | Plans | `tests/test_planner.py` | Unit+API | ✅ Step 8 |
| AC-73–76 | Substitutions | `tests/test_substitutions.py` | API | ⬜ Step 9 |
| AC-77–79 | Grocery | `tests/test_domain_grocery.py` | Unit | ✅ Step 2 |
| AC-80–81 | Grocery | `tests/test_grocery_service.py` | API | ⬜ Step 9 |
| AC-82–84 | Logging | `tests/test_nutrition_logs.py` | API | ⬜ Step 10 |
| AC-85–87 | Dashboard | `tests/test_dashboard.py` | API | ⬜ Step 10 |
| AC-88–89 | Data | `tests/test_data_controls.py` | API | ⬜ Step 11 |
| AC-90–96 | UI | `frontend/src/` | UI/E2E | ✅ Step 5 |
| AC-97 | Quality | `alembic upgrade/downgrade/check` | DB | ✅ Step 1 |
| AC-98 | Quality | `tests/test_layering.py` | Unit | ✅ Step 3 |
| AC-99 | Quality | CI check | CI | ⬜ Step 11 |
| AC-100 | Quality | Coverage reports | CI | ⬜ Step 11 |
| AC-101 | Quality | GitHub Actions CI | CI | ⬜ Step 12 |
| AC-102 | Quality | Regression fixtures | Unit | ⬜ Step 2 |
| AC-103 | Perf | `tests/test_performance.py` | Perf | ⬜ Step 11 |
| AC-104 | Security | `tests/test_logging.py` | Unit | ✅ Step 3 |
| AC-105 | Deploy | `docker compose up -d` | Deploy | ✅ Step 1 |
| AC-106 | Deploy | Seed + demo commands | Deploy | ⬜ Step 12 |
| AC-107 | Deploy | `/api/health` + health checks | Deploy | ✅ Step 1 |
| AC-108 | Deploy | Backup/restore test | Deploy | ⬜ Step 12 |
| AC-109 | Deploy | TLS proxy test | Manual | ⬜ Step 12 |
| AC-110 | Deploy | Second-device test | Manual | ⬜ Step 12 |
| AC-111 | Security | `.env.example` completeness | CI | ⬜ Step 12 |
| AC-112 | Deploy | E2E journey in CI | E2E | ⬜ Step 12 |
| AC-113 | Deploy | Public deployment (optional) | Manual | ⬜ Optional |
| AC-114–118 | Docs | README + docs review | Manual | ⬜ Step 12 |
