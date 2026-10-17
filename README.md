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

## Safety Thresholds

The following thresholds are **placeholders under review** — they are not authoritative:

| Threshold | Value | Status |
|---|---|---|
| `estimate_floor_kcal` | 1,500 kcal | Placeholder — cite a qualified source |
| `plan_minimum_kcal` | 1,200 kcal | Placeholder — cite a qualified source |

Sources to cite:
- Mifflin–St Jeor equation: TBD
- Activity factors: TBD
- Protein default (1.6 g/kg): TBD

## Known Limitations (v1)

- Adult confirmation is self-declared (no verified age check)
- No email verification or password reset
- Nutrient data is approximate (from USDA FoodData Central + IFCT)
- No density conversion in the grocery list (mass and volume stay separate)
- The greedy planner does not guarantee optimal plans
- No wearable integration, barcode scanning, or social features

## Documentation

- [`DECISIONS.md`](DECISIONS.md) — All design decisions
- [`docs/DATA_LICENCES.md`](docs/DATA_LICENCES.md) — Data sources and licences
- [`docs/test-plan.md`](docs/test-plan.md) — Acceptance criteria → test mapping
- [`docs/learning-log.md`](docs/learning-log.md) — Build log with quiz questions
- [`SPEC.md`](spec.md) — Full specification

## Licence

This project is for academic purposes.
