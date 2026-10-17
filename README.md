# Gym Workout Logger & Strength-Focused Diet Planner

A full-stack web application combining workout logging with strength analytics and a rule-based diet-plan generator.

> **Disclaimer:** This application provides informational estimates only. It is not medical advice and not a substitute for guidance from a registered dietitian or doctor.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16
- **Frontend:** React 19, TypeScript, Vite
- **Infrastructure:** Docker Compose, nginx, mkcert (TLS)

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Node.js 22+](https://nodejs.org/) (for frontend development)
- [Python 3.12+](https://www.python.org/) (for backend development)

### Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd "Gym workout logger"

# 2. Copy environment file and set secrets
cp .env.example .env
# Edit .env — change POSTGRES_PASSWORD, SECRET_KEY, etc.

# 3. Build and start everything
docker compose up -d --build

# 4. Open the app
# http://localhost:8080
```

### Seed Data & Demo

```bash
# Load the reviewed food/exercise catalogue
docker compose run --rm backend python -m app.seed

# Create a synthetic demo account (12 weeks of data)
docker compose run --rm backend python -m app.demo_user
```

### Development

```bash
# Backend
cd backend
pip install -e ".[dev]"
pytest -q
ruff check .
mypy .

# Frontend
cd frontend
npm install
npm run dev
npm run lint
npx tsc --noEmit

# Migrations
cd backend
alembic upgrade head
alembic check
```

## Environment Variables

See [`.env.example`](.env.example) for all required variables.

## Safety Thresholds & Scientific Citations (Rule S1–S10, AC-116)

All numeric thresholds are consolidated in `app/config.py` and cite peer-reviewed clinical and exercise science literature:

| Parameter | Value | Scientific Citation / Source |
|---|---|---|
| `estimate_floor_kcal` | 1,500 kcal | Dietary Guidelines for Americans (USDA/HHS); placeholder floor preventing extreme deficits |
| `plan_minimum_kcal` | 1,200 kcal | Clinical minimum safe energy threshold for sedentary adults without medical supervision |
| **BMR Formula** | Mifflin–St Jeor | Mifflin MD, St Jeor ST, et al. *Am J Clin Nutr.* 1990; 51(2):241–247 |
| **Activity Multipliers** | 1.2 to 1.725 | FAO/WHO/UNU Scientific Consultation on Human Energy Requirements (2004) |
| **Protein Target** | 1.6 to 2.2 g/kg | Morton RW, et al. *Br J Sports Med.* 2018; 52(6):376–384 (resistance training meta-analysis) |
| **Strength Surplus** | +5% TDEE | Helms ER, et al. *J Sports Med Phys Fitness.* 2015 (lean mass accrual without fat gain) |
| **e1RM Formula** | Epley | Epley B. *Boyd Epley Workout.* Lincoln, NE: Univ. of Nebraska; 1985 (valid for 1–12 reps) |

## Known Limitations (v1, AC-118)

Per specification AC-118, the initial release intentionally operates with the following explicit scope boundaries:
1. **Self-Declared Adult Confirmation:** Age verification relies on self-confirmation (Rule S2) rather than external KYC or identity document scanning.
2. **Authentication Scope:** No third-party OAuth, SMS, or email recovery in v1; accounts use server-side argon2id credentials and revocable HttpOnly cookies.
3. **Nutrient Approximation:** Reference values are sourced from USDA FoodData Central and IFCT; naturally occurring agricultural variations mean all micro and macro numbers are approximate.
4. **Volume-Mass Density Independence:** The grocery checklist aggregates identical units (`g` + `g`, `ml` + `ml`) but does not perform synthetic mass-to-volume conversions (e.g. converting `tbsp` of olive oil to `grams` without empirical food density tables).
5. **Greedy Planner Heuristic:** The meal plan generator uses a deterministic, explainable greedy scoring algorithm rather than an integer linear programming (ILP) solver; it finds feasible, high-variety plans quickly but does not claim mathematical global optimality.

## Documentation Index (AC-115, AC-116)

- [`docs/DECISIONS.md`](docs/DECISIONS.md) — Complete 20-decision engineering architecture log (D-01 to D-20)
- [`docs/DATA_LICENCES.md`](docs/DATA_LICENCES.md) — Data sources, public domain notices, and license tracking
- [`docs/test-plan.md`](docs/test-plan.md) — Acceptance criteria (AC-01 to AC-118) verification matrix
- [`docs/learning-log.md`](docs/learning-log.md) — Comprehensive viva learning log with design rationale & quiz questions
- [`spec.md`](spec.md) — Complete 634-line master specification

## Licence

Academic Project — Developed for undergraduate viva presentation and evaluation.

