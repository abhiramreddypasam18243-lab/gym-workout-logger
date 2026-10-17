# Learning Log

Each step adds an entry: what was built, why it's designed that way, one risk, and 3 quiz questions.

---

## Step 1 — Repo, Tooling, and Walking-Skeleton Compose Stack

**What was built:** Project structure with backend (FastAPI + SQLAlchemy + Alembic), frontend (React + Vite + TypeScript), and Docker Compose stack (PostgreSQL, backend, frontend/nginx). Health check endpoint at `/api/health`.

**Why it's designed this way:**
- **Modular monolith** (D-01): simpler than microservices but with clean layer boundaries (`domain` → `services` → `repositories` → `api`).
- **Async SQLAlchemy**: PostgreSQL with asyncpg for non-blocking database access, important when handling concurrent API requests.
- **Non-root containers** (D2): security best practice — if a container is compromised, the attacker has limited privileges.
- **Nginx as reverse proxy**: serves the SPA, proxies `/api/` to the backend, and adds security headers (SEC9).

**What could go wrong:** If the Alembic migration runs before PostgreSQL is fully ready, it will fail. That's why Docker Compose uses `depends_on` with `condition: service_healthy` and the database has a `pg_isready` health check.

**Quiz questions:**
1. Why do we use `depends_on: condition: service_healthy` instead of just `depends_on`? What would happen without the health check condition?
2. Why does the backend entrypoint run `alembic upgrade head` before starting uvicorn? What happens on the very first deploy vs subsequent deploys?
3. The nginx config has `try_files $uri $uri/ /index.html`. Why is this needed for a React SPA, and what would happen without it?

---

## Step 2 — Pure Domain Functions (Units, Strength, Nutrients, Targets, Grocery, Scoring)

**What was built:** Pure domain modules in `backend/app/domain/` with zero framework, database, or clock imports:
- `units.py` (AC-16): Exact `Decimal` mass conversions ($100\text{ lb} = 45.359237\text{ kg}$), round-trip consistency ($< 10^{-9}$), cooking volume units (D-15), and 1-decimal-place display formatting.
- `targets.py` (AC-19–21): Mifflin–St Jeor BMR, TDEE activity multipliers, +5% strength goal adjustment, macro split defaults ($1.6\text{ g/kg}$ protein, $25\%$ fat, remainder carbs), and energy floor detection ($< 1,500\text{ kcal}$).
- `scoring.py` (AC-63, AC-64): Candidate target fit deviation, multi-factor scoring formula with weights ($w_t, w_c, w_p, w_b, w_r$), and discrete serving size selection ($0.5$ to $3.0$ with ties going to the smaller size).
- `strength.py` (AC-39–41, AC-43): Epley e1RM formula (1–12 rep range), warm-up set exclusion, working volume summation, and chronological PR detection (first working set as baseline, strict inequality for PRs).
- `nutrients.py` (AC-45–47): Per-100g nutrient scaling, edible weight accounting, and recipe totals / per-serving breakdown.
- `grocery.py` (AC-77–79): Ingredient scaling by planned servings, segregation into incompatible unit families (`mass`, `volume`, `count`), and canonical aggregation with display thresholds ($1,000\text{ g} \to 1.2\text{ kg}$, $1,000\text{ ml} \to 1.5\text{ l}$).

**Why it's designed this way:**
- **Layering & Pure Functions (D-20, AC-98):** Domain functions do not import FastAPI, SQLAlchemy, or the system clock. They take explicit arguments and return plain values or dataclasses, guaranteeing determinism and lightning-fast test execution without mock databases.
- **Exact Decimals (D-05, AC-43):** Floating point binary fractions cause subtle arithmetic drift. Using `Decimal` guarantees exact calculations for fitness loads and nutritional targets.
- **Unit Family Segregation (AC-78):** Aggregating mass and volume requires ingredient density (e.g. 1 cup of flour $\ne$ 1 cup of honey). Without verified density metadata, attempting density conversion would corrupt recipe grocery lists; keeping them separate prevents errors.

**What could go wrong:** If workout sets are not ordered strictly chronologically before evaluating PRs (or if timestamps are null and set numbers are shuffled), a weaker subsequent set could be evaluated before a stronger one, corrupting the personal record progression and misidentifying the baseline set.

**Quiz questions:**
1. Why is Epley's formula ($e1RM = \text{load} \times (1 + \text{reps} / 30)$) restricted to $1 \le \text{reps} \le 12$, and why is $1\text{ rep}$ treated as an identity ($\text{load}$)?
2. In recipe nutrition calculations, why must `edible_weight_g` take precedence over purchased `quantity_g`, and how would ignoring this affect bone-in meat or unpeeled vegetables?
3. Why do we keep grocery quantities in separate unit families (`mass`, `volume`, `count`) rather than converting cups or tablespoons of an ingredient into grams?

