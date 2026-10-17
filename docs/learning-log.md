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

---

## Step 3 — Database Models, Migrations, Authentication, Sessions, CSRF, and Security (AC-01 to AC-13, AC-15, AC-97, AC-98, AC-104)

**What was built:**
- Full relational schema in `backend/app/models/` (24 entities: users, sessions, profiles, food constraints, cuisine preferences, exercises, routines, routine_exercises, workout_sessions, workout_exercises, workout_sets, foods, food_nutrients, food_allergens, recipes, recipe_ingredients, recipe_diet_tags, recipe_meal_types, nutrition_goals, meal_plans, planned_meals, planned_meal_items, nutrition_logs, nutrition_log_items).
- Initial schema Alembic migration: `backend/alembic/versions/001_initial_schema.py`.
- Argon2id password hashing and constant-time dummy verification for unknown emails (SEC1, SEC5, AC-01–03).
- Server-side revocable session cookies (`HttpOnly`, `SameSite=Lax`, `Secure` over TLS) with SHA-256 token hashing (SEC2, AC-03, AC-05).
- Double-submit CSRF token validation on all state-changing endpoints (SEC3, AC-06).
- Rate limiter restricting failed logins to 5 attempts per 15 minutes with `Retry-After` (SEC6, AC-04).
- TLS enforcement returning 403 `tls_required` for remote clients accessing credentials over plain HTTP (SEC7, AC-07).
- Ownership isolation matrix test harness verifying cross-user access returns 404 identical to non-existent resources (SEC4, AC-08).
- Strict Pydantic schemas with `extra="forbid"` preventing parameter injection like client-supplied `user_id` (SEC8, AC-09).
- Middleware enforcing 1 MB request body size limit returning 413 (SEC8, AC-13).
- Security response headers: CSP, nosniff, Referrer-Policy, X-Frame-Options: DENY, and restricted CORS (SEC9, AC-11).
- Profile validation enforcing ranges (height 50–260 cm, weight 20–400 kg) and IANA timezone verification (FR-01, AC-15).
- Domain purity test ensuring `app/domain` contains zero framework, DB, or clock dependencies (AC-98).
- Canary logging test verifying no password, token, session ID, or full email address is logged (SEC12, AC-104).

**Why it's designed this way:**
- **Defense in Depth:** Passwords are never stored in plaintext (Argon2id). Session tokens and CSRF tokens are stored only as SHA-256 digests; even a complete SQL dump yields zero usable session tokens.
- **Service/Database Layer Ownership:** Ownership authorization is never trusted to client-side filters. Querying by `(id, user_id)` ensures unauthorized accesses result in a uniform 404 Not Found, preventing IDOR attacks and information disclosure.
- **Constant-Time Verification:** When an email does not exist, verifying a dummy Argon2id hash prevents attackers from measuring server response times to enumerate registered accounts.

**What could go wrong:** If the frontend SPA omits the `X-CSRF-Token` header on mutating POST/PATCH/DELETE calls, requests fail with 403 `csrf_failed`. Additionally, if sessions are stored only in memory without database synchronization, restarting backend servers would invalidate active logins.

**Quiz questions:**
1. Why do we store only the SHA-256 hash of session and CSRF tokens in the database rather than the raw tokens generated by `secrets.token_urlsafe`?
2. How does checking a dummy password hash on unknown emails prevent timing side-channel attacks during login?
3. Why must ownership checks return 404 Not Found rather than 403 Forbidden when a user accesses a resource belonging to someone else?


## Step 4 — Catalogue Data, Provenance Validation, Atwater Checks, Idempotent Seeding, and Catalogue APIs (AC-48 to AC-55)

**What was built:**
- Curated seed catalogues in `backend/app/seed/data/`:
  - `exercises.json`: 35 exercises spanning all 7 primary movement patterns and muscle groups (chest, back, shoulders, quads, hamstrings, glutes, biceps, triceps, core).
  - `foods.json`: 48 whole and staple foods with full provenance (USDA FoodData Central FDC IDs, Indian IFCT codes), serving descriptions, raw/cooked states, and verification dates.
  - `recipes.json`: 20 high-protein recipes spanning 4 distinct cuisines (Indian, Italian, Mexican, American/East Asian), with at least 2 ingredients each, positive servings, and prep/cook times.
- Idempotent seed loader in `backend/app/seed/loader.py`:
  - Provenance validation checking `data_source`, `serving_description`, `state`, and `verified_at` (DL1, AC-49).
  - Pure domain Atwater 4-4-9 energy balance validation: $| \text{kcal} - (4P + 4C + 9F) | \le \max(20, 0.15 \times \text{kcal})$ (AC-50).
  - Recipe allergen union computation and incomplete allergen flagging on text-only ingredients (S9, AC-52).
  - Idempotent database loading: re-running the seed command produces 0 new inserts and preserves all counts (AC-51).
  - CLI runner `python -m app.seed` (D4, AC-106).
- Catalogue API endpoints in `backend/app/api/catalogue.py`:
  - `GET /api/exercises`: substring search (`q`), muscle and equipment filters, and pagination (AC-29).
  - `POST /api/exercises`: custom exercise creation with per-user case-insensitive uniqueness check (AC-30).
  - `GET /api/foods`: search by name and category with clear `is_approximate` labelling (AC-49, AC-53).
  - `DELETE /api/foods/{id}`: returns 409 Conflict if food is referenced in recipes, plans, or intake history (AC-55).
  - `GET /api/recipes`: filtering by cuisine, diet tag, meal type, and max total time, with per-serving nutrition dynamically computed using domain functions and complete allergen unions (AC-53).
- Database check constraints verifying non-negative nutrient amounts, positive servings, and positive ingredient quantities (AC-48).
- Immutable historical snapshots: `nutrient_snapshot` JSON preservation in `PlannedMealItem` and `NutritionLogItem` (AC-54).

**Why it's designed this way:**
- **Atwater Energy Consistency:** Bogus nutritional numbers (e.g., claiming 500 kcal for 10g protein and 0g carbs/fat) break target fit scoring in the diet planner. Validating energy against macronutrients ensures catalogue integrity.
- **Strict Allergen Unions:** A recipe's allergen list is computed directly from its resolved ingredient foods. When an ingredient is text-only (not mapped to a verified food item), the recipe is explicitly flagged with `has_incomplete_allergen_data = true`, enabling the planner's safety filters (S9) to exclude unverified meals for allergic users.
- **Historical Snapshot Invariance:** In nutrition logging, if a catalogue food's nutritional profile is updated months later, historical logs must reflect what was recorded on that day. Storing a frozen `nutrient_snapshot` prevents retroactive data drift.
- **Referential Integrity on Deletes:** Foreign keys configured with `ondelete="RESTRICT"` and API-level pre-checks ensure that deleting a catalogue item never cascades into destroying historical workout logs, meal plans, or recipes.

**What could go wrong:**
- If an ingredient in a recipe is deleted or renamed without maintaining foreign key restrictions, the recipe's nutrient calculations could crash with null references.
- If Atwater tolerances are set too stringently without accounting for dietary fiber or natural analytical variance, genuine whole foods from official tables (like legumes with 8g+ fiber per 100g) could be rejected during seeding.

**Quiz questions:**
1. What is the 4-4-9 Atwater energy balance equation, and why is an absolute and percentage tolerance ($\max(20\text{ kcal}, 15\%)$) necessary when validating real food composition data?
2. Why do historical intake logs and meal plans store a frozen JSON `nutrient_snapshot` rather than simply joining against the `foods` table on every query?
3. How does the system handle allergen safety when a recipe contains text-only ingredients (i.e. ingredients not linked to a verified food item)?

---

## Step 5 — Workout Logging, Routines, Keyset Pagination, and Responsive Titanium UI (AC-29 to AC-38, AC-90 to AC-96)

**What was built:**
- **Pydantic Validation & Atomic Transactions (`backend/app/schemas/workout.py`, `backend/app/api/workouts.py`):**
  - Validation enforcing reps $> 0$, load $\ge 0$, RPE strictly between 1.0 and 10.0 in 0.5 increments (accepting 7.5, rejecting 7.3 and 11.0), unique set numbers per exercise, set completion times $\ge$ session start time, and routine rep ranges (`rep_min <= rep_max`) (AC-32, AC-35).
  - Atomic workout session persistence: if any set is invalid or database failure occurs, the entire transaction rolls back cleanly, leaving zero orphaned sessions or sets (AC-33).
  - Cascade replacement on edits and strict ownership-scoped deletes leaving other users' data unaffected (AC-34).
  - Keyset history pagination using a composite cursor `(started_at, id)` ensuring zero duplicate or skipped sessions during concurrent inserts, verified with `(user_id, started_at)` index usage (AC-37, AC-38).
  - Routine duplication and template workout initialization pre-filling exercises with zero logged sets (AC-35).
- **Dark Titanium Design System & UI Components (`frontend/src/`):**
  - Glassmorphic dark gym titanium theme (`#090d16`, `#0f172a`, `#38bdf8`, `#10b981`, `#f59e0b`, `#f43f5e`) in `frontend/src/index.css`.
  - Zero horizontal overflow guaranteed down to 360px viewport width (AC-94).
  - Visible `:focus-visible` ring on all interactive elements for accessible keyboard navigation (AC-91).
  - Loading skeletons, empty states, and field-level error messages connected via `aria-describedby` across all views (AC-90).
  - Fast set logging with 1-click set copying that duplicates previous reps and load, taking $< 3$ interactions per set (AC-95).
  - Unit toggle and conversion: automatic live conversion between kilograms and pounds with 1-decimal formatting, storing canonical kg in the database (AC-16, AC-96).
  - Informational disclaimer banner (Rule S1, AC-28) and wellbeing controls (Rule S7: hide calories, pause nutrition, track body weight opt-in, professional guidance flag).

**Why it's designed this way:**
- **Atomic Multi-Row Logging:** A gym workout is a hierarchical entity (`session` $\to$ `workout_exercises` $\to$ `workout_sets`). Partial saves (e.g. logging a squat set without the exercise or session) result in corrupt volume and PR analytics. Running the entire hierarchy inside an ACID transaction ensures absolute data integrity.
- **Keyset vs Offset Pagination:** Traditional `OFFSET / LIMIT` pagination suffers from $O(N)$ scanning performance degradation on large tables and causes duplicate or missing items if new sessions are inserted while a user scrolls. Keyset pagination using `WHERE (started_at, id) < (cursor_date, cursor_id) ORDER BY started_at DESC, id DESC LIMIT 10` leverages the composite B-tree index in $O(\log N)$ time with complete stability.
- **Fast Set Entry (< 3 Clicks):** Gym users log sets between exhausting intervals with sweaty hands on a phone screen. Requiring users to re-type exercise names, weights, and reps on every set creates friction and leads to abandoned logging. Auto-duplicating the previous set's parameters allows logging a set in a single tap.

**What could go wrong:**
- In an async SQLAlchemy session with `expire_all()`, accessing an entity attribute outside an active transaction without eager loading triggers greenlet asynchronous I/O exceptions (`MissingGreenlet`).
- In keyset pagination, if timestamps are identical across multiple sessions created programmatically, sorting solely on `started_at` causes non-deterministic ordering; combining `(started_at, id)` breaks ties deterministically.

**Quiz questions:**
1. Why is keyset (cursor) pagination superior to offset-based (`OFFSET N LIMIT M`) pagination for an infinite-scroll workout history feed?
2. Why is RPE validated specifically to multiples of 0.5 between 1.0 and 10.0, and how does the backend enforce atomicity when logging a workout with 5 exercises and 20 sets?
3. How does the frontend ensure fast set entry (AC-95) and consistent unit conversion between metric (kg) and imperial (lb) without corrupting the canonical database storage?

---

## Step 6 — Strength Analytics Service, e1RM Trends, PR Detection, and Consistency (AC-39 to AC-44)

**What was built:**
- **StrengthAnalyticsService (`backend/app/services/strength.py`):**
  - Best e1RM trends computation per exercise, grouped by local date in user timezone, excluding warm-up sets, with transparent labelling (`is_estimated = True`), converting units dynamically for imperial (`lb`) users to 1 decimal place, returning an empty list with status 200 when no data exists (AC-39, AC-42, AC-96).
  - Exact Decimal preservation: exact decimal representation preserved in `e1rm_exact` (e.g. 82.5 kg × 3 reps gives exactly `90.75`, AC-43).
  - Chronological Personal Record (PR) evaluation: baseline established on first working set, strictly greater e1RM flagged as PR, equal e1RM not flagged, and automatic dynamic recomputation upon set deletion or modification (AC-41).
  - Weekly training consistency: calculates completed workout sessions per calendar week (Monday to Sunday) in user timezone; weeks with none return 0; sessions containing only warm-up sets are strictly excluded (AC-44).
- **Analytics API Router (`backend/app/api/analytics.py`):**
  - `GET /api/analytics/strength`: trend query by exercise and optional window.
  - `GET /api/analytics/consistency`: weekly session frequency vs weekly target.
  - `GET /api/analytics/prs/{exercise_id}`: chronological PR progression.
- **Frontend Strength Analytics Component (`frontend/src/components/StrengthAnalytics.tsx`):**
  - Movement and time window selectors.
  - Visual e1RM bar progression graph with max-scaling.
  - Accessible data table alternative right alongside the visual chart (AC-93).
  - PR milestones timeline highlighting baseline benchmark and PR records.
  - Weekly consistency grid displaying sessions against target with success badges.

**Why it's designed this way:**
- **Strict Inequality for PRs (AC-41):** Lifting the exact same calculated e1RM as a previous set does not demonstrate strength progression; requiring strictly greater e1RM ($e1RM > \max(prior)$) ensures milestones reflect genuine progress.
- **Warm-Up Exclusion from Metrics:** Warm-up sets (e.g. 40kg × 10 on bench press) are light preparation. Including them in volume, e1RM trends, or session counting would dilute training volume and register false sessions for warm-up-only warm-down days.
- **Dual Representation (`e1rm` vs `e1rm_exact`):** For UI displays, users expect human-readable rounded metrics (`90.8 kg` or `200.1 lb`), but analytics calculations, test assertions, and PR rankings must never accumulate floating-point rounding errors. Providing both ensures exact math alongside clean presentation.

**What could go wrong:**
- If user timezones are ignored and UTC dates are used to aggregate daily bests, a late-night session at 11:30 PM in New York (`America/New_York`) would be incorrectly grouped into the following UTC day, separating sets that occurred in the same physical gym session.
- If consistency counting does not verify the presence of working sets, a session with only warm-up mobility sets would increment the consistency count, violating rule AC-44.

**Quiz questions:**
1. Why does the system evaluate PRs dynamically on demand rather than storing a static boolean `is_pr` column on each set in the database?
2. How does the system ensure that a user working out at 11:45 PM in their local timezone has their sets credited to the correct calendar day rather than the following UTC date?
3. Why are warm-up sets strictly excluded from e1RM calculations, training volume summations, and weekly session consistency counts?


