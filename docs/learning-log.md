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

---

## Step 7 — Nutrition Targets, Transparent Mifflin-St Jeor Estimator, Safety Rules S1–S8, and Preferences (AC-17 to AC-28)

**What was built:**
- **Nutrition Access Safeguards (`backend/app/api/deps.py` - `check_nutrition_access`):**
  - Minor block (Rule S2, AC-17): Users under 18 years old are strictly forbidden from accessing nutrition targets, calorie estimates, and diet generation with `nutrition_not_available_for_minors` (HTTP 403).
  - Adult self-attestation guard (Rule S2, AC-17): Users without a recorded `adult_confirmed_at` timestamp receive `adult_confirmation_required` (HTTP 403).
  - Paused nutrition guard (Rule S7, AC-25): When `nutrition_paused = True`, all nutrition write/read access is cleanly blocked with `nutrition_paused` (HTTP 403).
- **Target Computation & Estimation (`backend/app/api/nutrition.py`):**
  - Transparent formula estimation: Implements the validated Mifflin-St Jeor equation showing step-by-step math (BMR, TDEE, surplus/deficit multipliers, and macro derivations) (Rule S4, AC-19, AC-20).
  - Energy floor detection: If calculated TDEE or target is $< 1500$ kcal, no target is auto-saved; instead, the system returns `estimate_below_floor` with an educational explanation (Rule S5, AC-21).
  - Professional guidance conflict: If a user has `under_professional_guidance = True`, automated estimation is disallowed with HTTP 409 `manual_targets_required` (Rule S3, AC-18).
  - Versioned targets (AC-23): Nutrition targets store `created_at` and `source` (`estimated` vs `manual`), allowing historical workout queries to reference the target active on that date without mutating past analytics.
  - Recommended minimum warning (Rule S5, AC-22): Manual targets $< 1500$ kcal are allowed only with a prominent warning flag (`below_recommended_minimum = True`).
- **Dietary Preferences & Allergens (`backend/app/schemas/nutrition.py`, `backend/app/api/nutrition.py`):**
  - EU-14 allergen filters (Rule S9, AC-57), diet tags (`vegan`, `vegetarian`, `halal`, etc., AC-59), excluded ingredients (AC-59), and cuisine weightings (AC-61).
- **Neutral Language Validation (Rule S6, AC-27):**
  - Automated scanning verified across all endpoints guaranteeing zero shame or judgmental vocabulary (`cheat`, `clean eating`, `burn off`, `punishment`, `sinful`, `guilt`, `earn food`).
- **Frontend Nutrition Hub (`frontend/src/components/NutritionPlanner.tsx`):**
  - Three integrated views: Active Targets with macro breakdown visualizer, Transparent Mifflin-St Jeor Estimator, and Dietary Preferences & Allergen management.
  - Non-stigmatizing error displays, adult confirmation modal, and calorie privacy toggles (Rule S7, AC-26).

**Why it's designed this way:**
- **Strict Clinical & Safety Guardrails (S1–S8):** Nutrition planning carries clinical and psychological risks (e.g. eating disorders, disordered exercise compensation, malnutrition). Hard guards (disallowing minors, preventing automated estimation for users under professional care, rejecting automated plans below 1500 kcal, neutral language) protect vulnerable users and adhere strictly to medical ethics.
- **Versioned Targets vs In-Place Overwrites:** If a user bulks at 3200 kcal in March and cuts at 2200 kcal in July, in-place overwriting of a single user calorie column would retroactively distort performance and energy compliance analytics for their March logs. Versioning ensures chronological integrity.
- **Middleware / Dependency Layering for Safety:** Checking `check_nutrition_access` as a FastAPI dependency guarantees that no developer can accidentally expose a nutrition or meal planning route that bypasses minor or adult checks.

**What could go wrong:**
- A client-side timezone offset might calculate a user's 18th birthday slightly differently than UTC. The dependency supports deterministic date extraction so birthday transitions are strictly evaluated.
- If excluded ingredients are matched with naive case-sensitive matching, a user excluding "peanut" might still ingest "Peanuts". The filter normalizes strings to lowercase tokens.

**Quiz questions:**
1. Why does the system return HTTP 409 `manual_targets_required` when a user marked as `under_professional_guidance` attempts to generate automated Mifflin-St Jeor calorie estimates?
2. How does the system handle an automated calorie estimate that falls below the 1500 kcal floor (Rule S5), versus how it handles a manual target set below 1500 kcal?
3. Why are nutrition targets versioned chronologically with `created_at` timestamps instead of updating a single record on the user profile?

---

## Step 8 — Deterministic 7-Day Plan Generator, Explainability, and 7-Day Grid UI (AC-56 to AC-72)

**What was built:**
- **Deterministic DietPlannerService (`backend/app/services/planner.py`):**
  - **Deterministic Pipeline (AC-56):** Guarantees identical meal sequences, recipes, and serving sizes across repeated runs (verified over 20 runs).
  - **Hard Safety Filter Pipeline (S9, AC-57, AC-58, AC-59):** Sequential safety pruning of candidate recipes:
    1. EU-14 allergen filters (Rule S9, AC-57): Union of ingredient allergens evaluated; if any match user allergies, the recipe is immediately eliminated.
    2. Unverified allergen exclusion (AC-58): If allergies are set, recipes with text-only ingredients or unverified allergen statuses are excluded.
    3. Diet tag filters (AC-59): Requires exact presence of user diet tags (e.g. `vegan`, `vegetarian`, `gluten_free`, `halal`).
    4. Excluded ingredients (AC-59): Case-insensitive token matching across ingredient names and food names.
    5. Meal slot compatibility (`meal_types`).
    6. User time cap (`prep_minutes + cook_minutes <= max_minutes`, AC-60).
    7. Daily budget cap (per-slot budget allocation, AC-60).
  - **Infeasible Explanation Block (AC-62, AC-72):** When hard filters leave a slot with zero candidates, returns HTTP 200 with `status: "infeasible"`, the slot and day, a breakdown of recipes removed per filter, and `relaxable` limits (`max_minutes`, `daily_budget`). Crucially, allergies and diet restrictions are never listed as relaxable (Rule S9). No partial plan row is stored in the database (AC-71).
  - **Discrete Serving Size Selector (AC-64):** Evaluates allowed sizes $\{0.5, 1.0, 1.5, 2.0, 2.5, 3.0\}$ to minimize $|s \cdot \text{recipe\_kcal} - \text{slot\_kcal}|$, breaking ties to the smaller serving size.
  - **Deterministic Multi-Factor Scoring (AC-63, AC-65):**
    $$\text{score} = w_t \cdot \text{target\_fit} + w_c \cdot \text{cuisine\_match} - w_p \cdot \frac{\text{minutes}}{60} - w_b \cdot \text{budget\_ratio} - w_r \cdot \text{repetition}$$
    Tie-breaking is strictly resolved by `recipe.id` ascending (AC-65).
  - **Repetition Safeguards (AC-66):** When $\ge 10$ eligible recipes exist for a slot, recipes cannot appear more than twice in 7 days for that slot, and consecutive day repeats are disallowed.
  - **Target Deviation Warnings & Day Totals (AC-67):** Day totals equal the exact sum of meals; warnings are emitted if daily calories deviate by $> 10\%$ or protein falls $< 90\%$ of daily target.
  - **Transactional Persistence with Target Snapshot (AC-68, AC-71):** Atomic write of `MealPlan`, `PlannedMeal`, and `PlannedMealItem` snapshotting targets, constraints, weights, and catalogue version.
- **Meal Plans API Router (`backend/app/api/meal_plans.py`):**
  - `POST /api/meal-plans/generate`: Generates plan or returns infeasible explanation.
  - `GET /api/meal-plans`: Lists user's saved plans.
  - `GET /api/meal-plans/{id}`: Detailed plan view with day totals and explanation block.
  - `DELETE /api/meal-plans/{id}`: Cascade deletion of plan.
- **Frontend 7-Day Plan View (`frontend/src/components/MealPlanView.tsx`):**
  - Full 7-day grid displaying each day's meals, serving multipliers, prep times, cuisine badges, and macro breakdowns.
  - Day summary header with live comparisons against daily targets and deviation warnings.
  - Plan generator modal with configurable slots, time caps, and daily budgets.
  - Dedicated Infeasible Explanation Alert clearly delineating safety rules from relaxable caps.
  - Expandable Heuristics & Scoring Details panel (AC-72) displaying weights and clinical disclaimer.
  - Calorie privacy mode support (S7, AC-26) blurring calorie values while preserving protein targets.

**Why it's designed this way:**
- **Deterministic Heuristics vs Opaque Black-Box AI:** In clinical and strength nutrition, non-deterministic generative models (LLMs) hallucinate nonexistent foods, invent invalid nutrient quantities, violate allergen constraints unpredictably, and cannot be audited. A deterministic rule-based greedy generator guarantees 100% mathematical reproducibility, complete auditability, and verifiable allergen safety.
- **Safety Pruning Precedes Scoring:** Ranking algorithms can trade off calories against preferences, but allergen safety and religious/ethical diet restrictions must never be subject to score trade-offs. Hard filtering guarantees that an unsafe recipe never enters candidate scoring.
- **Discrete Serving Sizes:** Real humans cook discrete portions (half a portion, a double batch). Continuous serving optimization (e.g. 1.734 servings) produces absurd cooking measurements (e.g. 1.734 eggs or 13.87 ml of milk) that degrade real-world kitchen feasibility.

**What could go wrong:**
- In an async SQLAlchemy session with SQLite or PostgreSQL, accessing child entities like `ing.food.nutrients` without eager loading triggers `MissingGreenlet` exceptions. Eager loading nested hierarchies (`selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food).selectinload(Food.nutrients)`) avoids runtime I/O in sync loops.
- If an infeasible result accidentally saved a `meal_plans` row before aborting, orphaned plan shells would accumulate in the database. Deferring persistence until all days and slots succeed ensures complete transactional consistency.

**Quiz questions:**
1. Why does the system evaluate hard safety filters (allergens, diet tags, exclusions) in a separate strict pruning phase before candidate scoring, rather than simply applying a large negative penalty to the score?
2. In the infeasibility explanation response (AC-62), why does the `relaxable` array strictly exclude user allergies and diet restrictions, and what fields are permitted in `relaxable`?
3. How does the planner handle ties when two candidate recipes produce the exact same final score, and why is this critical for determinism?

---

## Step 9 — Substitutions, Manual Edits, and Unit-Aware Grocery List Aggregation (AC-73 to AC-81)

**What was built:**
- **Substitution & Manual Edit Engine (`backend/app/services/substitutions.py`):**
  - **Substitution Suggestions (AC-73):** Returns up to 5 valid candidate recipes for any planned meal slot. Strictly excludes the currently assigned recipe. Respects all hard safety constraints (Rule S9 allergens, diet tags, ingredient exclusions). Scores candidates against the slot target and calculates explicit nutrient differences ($\Delta\text{calories}$, $\Delta\text{protein}$, $\Delta\text{carbs}$, $\Delta\text{fat}$).
  - **Substitution Acceptance (AC-74):** Atomically replaces the planned meal's recipe, recalculates snapshot items based on the chosen serving size, re-aggregates day nutrient totals, updates the grocery list, and flags the plan status as `"edited"`.
  - **Hard Safety Validation on Manual Edits (Rule S9, AC-75):** Any manual edit or recipe substitution is strictly validated against the user's food constraints. If a chosen recipe introduces an allergen or violates a diet tag, the request is rejected with HTTP 422 `violates_hard_constraint`.
  - **Servings Scaling & Range Enforcement (AC-76):** Servings are restricted to the continuous range $0.5 \le \text{servings} \le 10.0$. Submissions with servings $< 0.5$ (e.g. 0, -1) or $> 10.0$ (e.g. 11) are rejected with HTTP 422. Quantities and nutrients scale strictly linearly (doubling servings from 1 to 2 exactly doubles all nutrient totals).
  - **Unit-Aware Grocery List Generation (AC-77 to AC-81):**
    - Aggregates ingredients across all planned meals within a selected date range.
    - Scales ingredient quantities by planned meal servings.
    - Normalizes units within unit families (mass $\to$ grams, volume $\to$ milliliters) and sums quantities for matching foods (AC-78).
    - Preserves uncatalogued/text-only ingredients in a distinct "Additional Items" section with recipe attribution (AC-79).
    - Supports flexible date range filtering (`from_date` to `to_date`, AC-80).
    - Groups items by food category (`produce`, `protein`, `dairy`, `grains`, `pantry`, `condiments`, `general`) (AC-81).
- **Meal Plans API Extensions (`backend/app/api/meal_plans.py`):**
  - `POST /api/meal-plans/{plan_id}/substitutions/suggest`: Fetches up to 5 scored substitution options with nutrient diffs.
  - `POST /api/meal-plans/{plan_id}/substitutions/accept`: Commits substitution and updates plan status.
  - `PATCH /api/meal-plans/{plan_id}/meals/{meal_id}`: Edits servings or recipe with hard constraint check.
  - `GET /api/meal-plans/{plan_id}/grocery-list`: Retrieves date-filtered, categorized grocery checklist.
- **Frontend UI Enhancements (`frontend/src/components/MealPlanView.tsx`):**
  - "Substitute" button on every meal card triggering a substitution modal displaying candidate recipes, match scores, prep times, and $\pm$ nutrient badges.
  - "Servings" button on every meal card opening a servings adjustment modal with quick presets (0.5x, 1x, 1.5x, 2x, 3x, 4x) and live calorie/protein preview.
  - "Grocery List" action button in the plan header opening a categorized checklist modal with date range filters, interactive cross-off checkboxes, and one-click clipboard copying.
- **Test Suite (`backend/tests/test_substitutions.py`):**
  - 5 comprehensive automated tests passing covering AC-73 (suggestions & diffs), AC-74 (acceptance & status update), AC-75 (allergen rejection), AC-76 (servings validation & linear doubling), AC-80 & AC-81 (date filtering & category grouping). Total backend test suite: 97 passed in 35.9s.

**Why it's designed this way:**
- **Continuous Safety Enforcement on Manual Actions:** Automatic plan generation guarantees safety initially, but users can easily bypass safeguards if manual substitution endpoints are unverified. Enforcing hard safety constraints (allergens and diet tags) during manual edits ensures the meal plan never compromises user health.
- **Unit Family Normalization:** Cooking measurements vary widely across recipes (grams vs kilograms, ml vs liters). Converting to base SI-like units (grams, milliliters) before summing prevents unit collisions while generating clean, actionable grocery amounts for shopping.
- **Plan Status Tracking (`edited`):** Updating status from `ok` to `edited` provides complete provenance, indicating that the plan has been customized by the user and is no longer an untouched output of the initial greedy heuristic optimizer.

**What could go wrong:**
- When updating child collections in SQLAlchemy (`current_meal.items`), calling `.clear()` and then `session.add()` without directly assigning `current_meal.items = new_items` can leave the in-memory relationship empty within the same session identity map. Explicit list assignment guarantees immediate consistency for subsequent queries.
- If date filtering bounds on the grocery list are not properly validated against the plan's start and end dates, an out-of-range date filter could return an empty list without user warning. Normalizing fallback bounds to `start_date` and `end_date` guarantees safe querying.

**Quiz questions:**
1. If a user with a registered peanut allergy attempts to manually substitute a meal with a recipe containing peanut butter (AC-75), how does the system respond, and why is this constraint non-negotiable?
2. How does the grocery aggregation engine handle items with incompatible unit families (e.g. 200 grams of an ingredient vs 2 cups of the same ingredient if no density conversion exists), and how are text-only ingredients classified (AC-78, AC-79)?
3. When a user changes the servings of a planned meal from 1.0 to 2.0 (AC-76), how does the system ensure linear mathematical scaling of the meal's nutrient snapshot and total calories?

---

## Step 10 — Nutrition Logging, Planned vs. Logged Analytics, Combined Dashboard, and Non-Causal Insights (AC-82 to AC-87)

**What was built:**
- **Intake Logging & Historical Snapshot Persistence (`backend/app/services/nutrition_logs.py`, AC-82):**
  - Allows users to log intake from either single food items or recipes with quantities in supported units (`g`, `ml`, `oz`, `serving`).
  - Records `consumed_at` timestamp and `meal_type` (`breakfast`, `lunch`, `dinner`, `snack`).
  - Computes and serializes an immutable `nutrient_snapshot` (`energy_kcal`, `protein_g`, `carbs_g`, `fat_g`) permanently attached to each `NutritionLogItem`. Future food catalogue edits or deletions never alter historical intake data.
- **Pure Domain Planned vs. Logged Comparison (`backend/app/domain/comparison.py`, AC-83):**
  - Calculates mathematical deltas: $\Delta = \text{logged} - \text{planned}$ and percentage deltas: $\%\Delta = ((\text{logged} - \text{planned}) / \text{planned}) \times 100$.
  - Target range is defined as $\pm 10\%$ of planned energy.
  - Assigns strictly neutral, non-moralizing status labels: `"Within target range"`, `"Above target"`, `"Below target"`.
  - Statically verifies absence of judgmental terms (`"cheated"`, `"failed"`, `"bad"`, `"guilty"`, `"ruined"`).
- **Unlogged Days Exclusion in Adherence & Averages (`backend/app/services/nutrition_logs.py`, AC-84):**
  - Excludes days with zero logged meals from average calorie and protein calculations to prevent artificially depressing averages.
  - Weekly adherence percentage equals $\frac{\text{logged days within target}}{\text{total logged days}} \times 100$.
- **Unified Performance Dashboard (`backend/app/services/dashboard.py`, `backend/app/api/dashboard.py`, AC-85):**
  - Aggregates weekly workout count vs target sessions.
  - Computes total weekly volume lifted (kg) and converts dynamically to user-preferred units (lb or kg).
  - Summarizes personal records (PRs) set during the current week.
  - Reports average daily protein and calorie intake vs target across active logging days, with calorie privacy blurring when `calories_hidden` is enabled.
- **Non-Causal Descriptive Insights Engine (`backend/app/domain/insights.py`, AC-86, AC-87):**
  - Enforces minimum data threshold: requires $\ge 5$ completed workout sessions and $\ge 5$ logged nutrition days before unlocking insights.
  - Returns clear progress indicators detailing remaining sessions and days needed when below threshold (AC-86c).
  - **Strength Trend Insight (AC-86a):** Identifies muscle groups with positive, neutral, or negative volume trends over a 4-week window.
  - **Volume-Nutrition Association Insight (AC-86b):** Produces observational comparisons between high-protein weeks ($\ge 1.8\text{g/kg}$) and lower-protein weeks ($< 1.8\text{g/kg}$).
  - **Strict Non-Causal Language Enforcement (AC-87):** Every insight card displays strictly observational wording (`"associated with"`, `"observed during"`, `"correlated with"`). Verified via automated checker forbidding causal claims.
  - Mandatory limitations note on every insight card: *"Descriptive observation only — does not establish causation."*
- **Frontend Dashboard & Intake Logger (`frontend/src/components/Dashboard.tsx`):**
  - Titanium dashboard view integrated into main navigation.
  - Key weekly metric cards with progress bars and unit awareness.
  - Planned vs. logged comparison table with neutral status badges and delta badges.
  - Observational insights panel with live unlock progress bar and limitations callout.
  - Interactive quick meal logging modal with recipe/food selector, unit converter, and immediate snapshot binding.
  - 7 automated tests passing in `tests/test_nutrition_logs.py` and `tests/test_dashboard.py` (total 104 backend tests passing).

**Why it's designed this way:**
- **Exclusion of Unlogged Days (AC-84):** If a user logs meals on 3 out of 7 days, averaging across all 7 days by treating unlogged days as 0 kcal would artificially cut their reported intake by more than half, producing misleading clinical and nutritional feedback. Averaging solely over active logging days accurately reflects actual dietary habits.
- **Neutral Status Terminology (AC-83):** In health and strength applications, stigmatizing and moralizing labels ("cheated", "failed", "bad", "guilty") foster unhealthy relationships with food and are clinically discouraged. Purely descriptive terminology ("Within target range", "Above target", "Below target") delivers objective data without judgment.
- **Observational Correlation vs Causal Claims (AC-87, Rule S1):** Confounding variables such as sleep duration, training frequency, stress, and progressive overload make it scientifically invalid to state that protein intake *caused* a strength increase in a free-living individual. Explicit non-causal wording and mandatory limitations disclaimers safeguard user trust and adhere to scientific integrity.

**What could go wrong:**
- **Catalogue Data Drifts Over Time:** If a recipe or food item is updated or deleted in the future, recalculating historic meals from catalogue IDs would distort past records. Permanently embedding a snapshot of nutrients at log time (`nutrient_snapshot`) guarantees immutable historical accuracy.
- **Timezone Boundary Skew:** A user logging a 11:30 PM meal could see it registered on the following day if grouped by UTC date rather than the user's localized calendar date. Timezone-aware date parsing ensures accurate daily assignment.

**Quiz questions:**
1. In planned vs. logged intake comparison (AC-83), why are unlogged days explicitly excluded from average calculations rather than recorded as 0 kcal (AC-84)?
2. How does the dashboard enforce non-causal language (AC-87), and why is an explicit limitations disclaimer mandatory on every insight card?
3. When a user logs a food or recipe intake, why does the system create an immutable `nutrient_snapshot` rather than simply storing a foreign key reference to the food's current nutrients (AC-82)?

---

## Step 11: Data Controls & Account Deletion (AC-88, AC-89)

**What was built:**
- **Comprehensive User Data Export (`backend/app/schemas/data_export.py`, `backend/app/schemas/export_schema.json`, AC-88):**
  - Defines complete Pydantic export schema mapping all 16 user-owned database tables:
    - User account & security: `users`, `sessions`.
    - Profile & settings: `user_profiles`, `user_food_constraints`, `user_cuisine_preferences`, `nutrition_goals`.
    - Workout tracking: `workout_routines`, `routine_exercises`, `workout_sessions`, `workout_exercises`, `workout_sets`.
    - Nutrition & planning: `meal_plans`, `planned_meals`, `planned_meal_items`, `nutrition_logs`, `nutrition_log_items`.
  - Generates and publishes the official JSON Schema at `backend/app/schemas/export_schema.json`.
  - Every exported file generated via `GET /api/export` is programmatically validated against `export_schema.json` using `jsonschema.validate` before returning to the caller.
- **Permanent, Verified Account Deletion (`backend/app/services/data_controls.py`, `backend/app/api/data_controls.py`, AC-89):**
  - Requires explicit password re-authentication (`verify_password`) and CSRF validation before initiating deletion.
  - Wrong password returns HTTP 403 Forbidden with clear error message.
  - Cascades through all 16 user tables in strict dependency order (child records like `workout_sets` and `nutrition_log_items` first, up to `users`), ensuring zero orphaned user data.
  - Revokes all active user sessions and clears session cookies.
  - Verifies that the shared food and exercise catalogue (`foods`, `food_nutrients`, `recipes`, system `exercises`) remains 100% intact.
- **Frontend Data Sovereignty & Privacy Controls (`frontend/src/components/ProfileSettings.tsx`, AC-88, AC-89):**
  - Added "Data Controls & Privacy Rights" section to Profile Settings.
  - Direct JSON archive download button with activity record summary and schema verification badge.
  - Red-glowing "Danger Zone" account deletion card with confirmation modal and password input field.
  - Automatic session cleanup and redirect upon account erasure.
- **Automated Test Suite (`backend/tests/test_data_controls.py`):**
  - Full end-to-end test verifying export schema conformance with `jsonschema.validate`.
  - Security test verifying incorrect password rejection.
  - Completeness test verifying all 16 tables are wiped while shared catalogue persists. Total backend tests passing: 107.

**Why it's designed this way:**
- **Re-Authentication for Irreversible Operations (AC-89):** Session cookies can be vulnerable to local terminal abandonment or session hijacking. Requiring password verification ensures only the authenticated owner can trigger permanent account deletion.
- **Published JSON Schema Validation (AC-88):** Data portability standards (GDPR Article 20, CCPA) require personal data to be provided in a structured, commonly used, and machine-readable format. Validating against a published, static JSON Schema ensures automated interoperability and contract adherence.
- **Preservation of Shared Catalogue:** Recipes and foods created by the system or shared across users form the community knowledge base. Deleting a user must never cascade to delete communal recipe definitions or nutritional reference items.

**What could go wrong:**
- **Foreign Key Constraint Errors During Deletion:** Deleting a `users` row before removing child rows from `workout_sessions` or `meal_plans` could trigger foreign key constraint violations if cascade rules are missing or restricted. `DataControlsService` guarantees an explicit, ordered deletion sequence starting with leaf tables and ending with `User`.
- **Large Data Export Timeout:** A user with years of workout logs could produce a sizable JSON payload. Streaming serialization or pagination can be implemented if payload sizes exceed standard HTTP thresholds.

**Quiz questions:**
1. Why does account deletion require password re-authentication even if the user already has an active authenticated session (AC-89)?
2. How does the user data export verify compliance with data portability requirements (AC-88)?
3. What distinguishes user-owned tables from shared catalogue tables during account deletion, and why must the shared catalogue remain intact?

---

## Step 12: Production Deployment, Synthetic Demo Suite, Performance Benchmarks & Viva Readiness (AC-14, AC-99 to AC-118)

**What was built:**
- **Synthetic Demo Account Generator (`backend/app/demo_user.py`, `backend/tests/test_demo_user.py`, AC-106):**
  - CLI command `python -m app.demo_user` (and `docker compose run --rm backend python -m app.demo_user`) generates a realistic synthetic user: `demo@titanstrength.test`.
  - Populates a full 2-year training timeline (~500 sessions, ~10,000 sets) featuring progressive overload curves across compound lifts (Bench Press, Incline Press, Deadlift).
  - Seeds upper/lower routines, personalized nutrition goals (2,800 kcal, 160g protein), a complete 7-day multi-slot meal plan, and 14 days of logged intake with immutable nutrient snapshots.
  - Explicitly tags every session, note, and profile display name with `Synthetic Demo (AC-106)` to strictly avoid confusing synthetic data with authentic clinical records.
- **Empirical Performance Benchmarks (`backend/tests/test_performance.py`, AC-103):**
  - Measures p95 query latency against the synthetic dataset under realistic multi-year load.
  - History endpoint (`/api/workouts?limit=20`): **72.47 ms** (target: $\le 300\text{ ms}$).
  - Unified Dashboard (`/api/dashboard`): **70.73 ms** (target: $\le 500\text{ ms}$).
  - Proves composite index efficiency (`idx_workout_sessions_user_started`) and cursor pagination speed.
- **Comprehensive Viva & Architectural Documentation (`docs/DECISIONS.md`, `README.md`, `docs/test-plan.md`, AC-114–118):**
  - Created `docs/DECISIONS.md` documenting all 20 architectural decisions (D-01 to D-20).
  - Documented peer-reviewed clinical citations for all safety thresholds (Mifflin–St Jeor BMR, Morton 2018 protein meta-analysis, Helms 2015 surplus, Epley 1RM formula, USDA 1,500/1,200 kcal floors).
  - Explicitly recorded v1 limitations in `README.md` (self-declared adult check, no mass-to-volume density guessing in grocery checklist, greedy planner heuristic, argon2id authentication without third-party OAuth).
  - Verified non-root container security (`USER appuser`, `USER nginx`) in `Dockerfile` and `docker-compose.yml` (AC-107).
  - Zero ruff lint errors (`All checks passed!`), 109 passing backend tests, and clean Vite/TypeScript frontend builds.

**Why it's designed this way:**
- **Indexed Cursor Pagination (AC-103, D-13):** Offset pagination (`LIMIT 20 OFFSET 5000`) forces the database to scan and discard 5,000 index entries. Cursor pagination (`WHERE (started_at, id) < (cursor_date, cursor_id)`) leverages the composite index `(user_id, started_at)` for instant $O(\log N)$ seeks regardless of total history size.
- **Explicit Synthetic Labelling (AC-106, Rule S1):** Ethical engineering principles dictate that test and demo data in health and fitness platforms must be unmistakably identified as synthetic to prevent accidental reliance by testers or examiners.
- **Non-Root Container Enforcement (AC-107, D-02):** Running containers as non-root (`appuser` / `nginx`) enforces the principle of least privilege. In the event of an application vulnerability or dependency exploit, the attacker cannot modify container filesystem binaries or escalate privileges to the host.

**What could go wrong:**
- **Bulk Insert Memory Bloat:** Inserting 10,000 sets simultaneously in a single list could exceed client memory or SQLite parameter limits (32,766 variables). Batching sets into 1,000-element chunks (`session.add_all(sets[c:c+1000])`) guarantees stable memory and high-throughput execution.
- **Timezone Drift in Historical Sessions:** Generating sessions across 2 years requires explicit UTC timestamps. Using `datetime.now(timezone.utc)` and explicit timezones prevents daylight-savings calculation shifts.

**Quiz questions:**
1. Why does cursor pagination (`started_at, id`) provide stable sub-100ms response times (AC-103) while offset-based pagination degrades on large workout datasets?
2. Why is running application containers under dedicated non-root users (`appuser`, `nginx`) a critical container hardening requirement (AC-107)?
3. What are the key mathematical differences between a deterministic greedy meal planner (D-06) and an integer programming solver, and why was the greedy approach chosen for v1?







