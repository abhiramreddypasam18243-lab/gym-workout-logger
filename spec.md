# SPEC.md: Gym Workout Logger and Strength-Focused Diet Planner

**Version:** 1.0 (draft, based on *Advanced Gym Workout Logger + Strength-Focused Diet Planner: Updated Project Blueprint*)
**Last updated:** 2026-10-16
**Methodology:** Spec-Driven Development. Every requirement has an ID, and every acceptance criterion (AC) becomes at least one automated test or one recorded measurement.

> Numbers marked *initial* (thresholds, weights, targets) are starting values. If you change one after measuring, record the change in the Decisions Log (section 18). Safety thresholds in section 3 are placeholders for you to review against a qualified source and cite in the README; they are not professional advice.

---

## 1. Overview

A full-stack web application that combines two things in one place: a **workout logger** with strength analytics (sets, reps, load, estimated one-rep max, personal records, volume, consistency) and a **rule-based diet-plan generator** that builds editable 7-day, multi-cuisine meal plans from a reviewed food and recipe catalogue, with substitutions, a grocery list, and a way to log what you actually ate.

The first release favours **correctness, explainability and testability over opaque AI**. Every number the app shows can be traced to a formula, a catalogue value with a recorded source, or a setting the user chose. The planner is a deterministic scorer with hard safety filters (allergies first), not a promise of an optimal plan, and the app is informational, not medical nutrition advice and not a promise of strength gains.

### Aim

Build a secure, well-tested full-stack application that lets a gym user record training, see honest strength trends, and generate and adjust meal plans that respect their allergies and preferences, with clear explanations, protective safety rules, and a deployment you can open in a browser on your computer or local network.

### Inputs

| Input | Details |
| --- | --- |
| Account and profile | Email, password, display name, timezone, units (kg or lb), optional height, weight and birth date, activity level, goal, and wellbeing settings (section 3) |
| Training data | Exercises, routines, sessions and sets (reps, load, optional RPE, rest, warm-up flag) |
| Nutrition preferences | Cuisines (several, with a preference level), diet tags, allergies, excluded ingredients, budget, preparation-time limit, target calories and macros |
| Meal plan actions | Generate, edit servings, substitute, accept or reject suggestions |
| Intake logs | What the user actually ate, by food or recipe and quantity |
| Seed catalogue | Reviewed exercises, foods with nutrient values and provenance, and recipes (section 4) |
| Configuration | Environment variables: database URL, secrets, allowed origin, registration switch, demo mode |

### Outputs

| Output | Details |
| --- | --- |
| Workout history and strength analytics | Per-exercise estimated 1RM, personal records, volume and trends, with every estimate labelled |
| Nutrition targets | Editable targets, with the inputs and assumptions that produced any estimate |
| Meal plans | 7-day plans with per-meal and per-day nutrient totals, warnings, and an explanation of the filters and scoring used |
| Substitution options | Eligible alternatives with nutrient differences |
| Grocery list | Aggregated ingredients across chosen days, with units kept consistent |
| Dashboard and insights | Consistency, strength trends, planned versus logged nutrition, and explainable observations with their time window, sample size and limitations |
| Data export | A complete JSON export of the user's data, and verified account deletion |
| Deployed service | The web application, running in containers at `http://localhost:8080` (and over HTTPS on the local network) |

### Requirements at a glance

- **Functional:** FR-01 to FR-20 (section 12), including the blueprint's FR-01 to FR-15.
- **Safety, wellbeing and privacy:** S1 to S10 (section 3).
- **Data rules:** DL1 to DL4 (section 4).
- **Security:** section 10. **Deployment:** D1 to D8 (section 11).
- **Non-functional:** section 15.
- **Acceptance criteria:** AC-01 to AC-118 (section 13), mapped to the blueprint's requirements in section 14.

## 2. Goals, Scope and Non-Goals

**Goals**
1. Accounts with strict per-user data isolation.
2. An exercise catalogue, routines, session and set logging, personal records, estimated 1RM and volume.
3. A reviewed food and recipe catalogue with nutrient values and provenance.
4. Nutrition profile, editable targets, and protective safety rules.
5. A deterministic, explainable, editable 7-day plan generator with allergy-first filtering.
6. Substitutions with recalculated totals, and a unit-aware grocery list.
7. Intake logging, and planned versus actual comparison.
8. A dashboard and descriptive insights that avoid causal claims.
9. Export and deletion of user data.
10. A tested, documented, deployed system.

**Non-goals (v1)**
- Medical diagnosis, treatment plans, eating-disorder management or clinical nutrition advice.
- Weight-loss or calorie-deficit goals (decision D-11); supported goals are `maintain` and `build_strength`.
- Guaranteed optimal plans or guaranteed strength gains.
- Wearable integration, barcode scanning, payments, social features, AI chat, and real-time nutrition data from third-party providers.
- Email verification, password reset and social login (documented limitations).

**Stretch** (only after every required criterion passes): an integer-programming planner, a nutrition-and-strength association insight (with strong guardrails), rest timers, a custom-food editor, idempotency keys for workout creation, and a public demo deployment.

## 3. Safety, Wellbeing and Privacy Rules

This app touches food, body data and health-adjacent decisions, so these rules are requirements, not polish.

| ID | Rule |
| --- | --- |
| **S1 Informational notice** | Every target, plan, log summary and insight screen, and every plan API response, carries a notice that estimates are informational and not medical advice, and that the app is not a substitute for a registered dietitian or doctor. |
| **S2 Adults only for nutrition planning** | Nutrition targets, plan generation and estimates require the user to confirm they are 18 or older (`adult_confirmed_at`). If a birth date is given and shows the user is under 18, nutrition planning and estimates are disabled for that account (`nutrition_not_available_for_minors`), with a message recommending guidance from a parent or guardian and a qualified professional. Workout logging and strength analytics stay available. The confirmation is self-declared, which is a documented limitation. |
| **S3 Professional-guidance flag** | A profile flag `needs_professional_guidance` (a yes or no only; no condition details are collected) disables estimate-based targets. Targets must then be entered manually, with a banner saying to follow the guidance of the user's professional. |
| **S4 Estimated targets are optional and transparent** | Estimates use the Mifflin–St Jeor equation, an activity factor and a goal adjustment (section 5.4), and always display their inputs, formula and assumptions. The user can ignore and edit them. |
| **S5 Energy floor** | The app never *suggests* an estimated target below `estimate_floor_kcal` (*initial*: 1,500 kcal); it reports `estimate_below_floor` and asks the user to enter a target manually or seek guidance. A manual target below that value is saved with a warning. Plan generation is **refused** below `plan_minimum_kcal` (*initial*: 1,200 kcal). Review both numbers against a qualified source and cite it in the README. |
| **S6 No deficit goals** | There is no weight-loss goal, no deficit calculation and no "calories to lose" language in v1. |
| **S7 Wellbeing settings** | The user can (a) **hide calorie numbers** everywhere in the UI (macros such as protein stay visible; the planner still uses calories internally), (b) **pause nutrition** (nutrition features are switched off, training continues, data is kept), and (c) track body weight only by **opting in**: no weight is requested or charted by default, and nothing requires it except the optional estimate, which asks at the moment of use. |
| **S8 Neutral language** | Nutrition feedback is descriptive, not judgemental: "within your range" and "below your range", never "failed", "cheated", "bad", "guilt" or streak-loss messaging. A test scans UI strings for a banned word list. |
| **S9 Allergy handling** | Allergies and explicit exclusions are hard filters. Catalogue data can be incomplete, so items with unknown or unverified allergen status are excluded when the user has any allergy (setting `exclude_unverified_allergens`, default on), and every plan carries a reminder to check labels. |
| **S10 Privacy** | Collect only what is needed. Birth date, height, weight and sex-for-estimate are all optional. Logs never contain passwords, tokens or full email addresses. Users can export and delete everything (FR-15). |

## 4. Data Rules and Licences

| ID | Rule |
| --- | --- |
| **DL1 Recorded sources** | Every food has `data_source`, a `source_reference` where possible, a serving basis, a raw or cooked state, and a `verified_at` date. Values that are estimates or imputed are flagged `approximate` and labelled that way in the API and UI. |
| **DL2 Licensed data only** | Nutrient data comes from sources whose licence permits this use, recorded in `DATA_LICENCES.md`. Government composition tables such as USDA FoodData Central are commonly public domain, but check each source and each table's licence yourself; if a licence is unclear, do not use the data. |
| **DL3 Original recipes** | Recipes are written by you or have a licence that permits reuse, each with a `source_note`. Do not copy recipes from websites or books. |
| **DL4 No invented values** | Seed nutrient values must come from a recorded source. Values invented for tests live only in clearly marked test fixtures and never in the seed catalogue. |

## 5. Domain Rules

### 5.1 Units, time and money
- Mass is stored in **kilograms** and rendered as kg or lb by the user's setting; `1 lb = 0.45359237 kg` exactly. Nutrient amounts are stored per 100 g. Cooking volumes use `1 tsp = 5 ml`, `1 tbsp = 15 ml`, `1 cup = 240 ml` (decision D-15).
- All timestamps are stored in UTC. Every "day" or "week" a user sees is computed in the user's IANA timezone (weeks are ISO weeks, Monday to Sunday, in that timezone).
- Calculations use exact decimals (`Decimal` in Python, `NUMERIC` in the database); the API transmits decimals as **strings**. Rounding happens only for display, to 1 decimal place (half-up) unless stated.
- Money is stored as integer minor units with a currency code; costs are approximate and labelled so.

### 5.2 Strength analytics
- **Estimated 1RM (Epley):** `e1RM = load × (1 + reps / 30)`. For `reps = 1`, `e1RM = load`. It is computed only for working sets with 1 to 12 reps (beyond that the estimate is unreliable and reported as `null` with reason `rep_range`), and always labelled "estimated".
- **Volume:** `load × reps`, summed over working sets only. Warm-up sets (`is_warmup = true`) are excluded from volume, e1RM and PRs.
- **Personal record:** a working set is a PR if its e1RM is **strictly greater** than the best e1RM of all earlier working sets of the same exercise for the same user (ordered by `completed_at`, then set number). The first working set is the **baseline** and is not flagged. Equal values are not PRs.
- **Consistency:** the sessions per week, counting only completed sessions with at least one working set; weeks with none show 0. An optional `weekly_session_target` is displayed as a neutral reference.

### 5.3 Nutrition calculation
- `nutrient = (edible weight in g / 100) × nutrient per 100 g`.
- A recipe's per-serving nutrients are the sum over ingredients divided by the recipe's `servings`. An ingredient with `edible_weight_g` uses that weight instead of the purchased quantity.
- Foods record whether values are for raw, cooked or as-sold items; a recipe ingredient uses the state stated for it.
- Totals for a meal or day are sums of item nutrient snapshots; they are never recomputed from the live catalogue for historical records.

### 5.4 Targets
- **Estimate (optional):** `BMR = 10 × weight_kg + 6.25 × height_cm − 5 × age + s`, with `s = +5` (male), `−161` (female), or `−78` (unspecified, the midpoint, shown as an assumption). `TDEE = BMR × activity factor` (sedentary 1.2, light 1.375, moderate 1.55, very active 1.725). Goal adjustment: `maintain` 0%, `build_strength` +5%. Calories are rounded to the nearest 10.
- **Protein** defaults to 1.6 g per kg of body weight; **fat** to 25% of calories (÷ 9 kcal per g); **carbohydrate** is the remaining calories (÷ 4 kcal per g). All grams round to the nearest 1 g. Every default is editable, and the rationale text states each assumption. Cite your source for these defaults in the README.
- Targets are **versioned**: a change creates a new `nutrition_goals` row with an `effective_from` date; the active target on a date is the latest row on or before it.

### 5.5 Plan generation (deterministic greedy)

**Inputs:** the active targets, preferences, hard constraints, number of days (default 7), meal slots (default breakfast, lunch, dinner, snack), optional maximum minutes per recipe, and optional daily budget.

**Slot shares of daily targets (initial):** breakfast 25%, lunch 30%, dinner 30%, snack 15%.

**Step 1: hard filters (safety first).** A recipe is a candidate for a slot only if it passes all of these:
1. No ingredient carries any of the user's allergens, and (with `exclude_unverified_allergens` on and any allergy set) every ingredient has verified allergen data and a catalogue link (text-only ingredients are excluded).
2. It satisfies every diet tag (vegan, vegetarian, pescatarian, halal, kosher, gluten-free, lactose-free, and so on) and contains no excluded ingredient.
3. It is allowed for the slot (`meal_types`).
4. If a time cap is set, `prep_minutes + cook_minutes` is within it; if a daily budget is set, the recipe's cost fits the slot's share of it.

Allergy, diet and exclusion filters are **safety filters**. Time and budget are **user hard caps** applied when set. Cuisine preference and variety are **ranking factors only**.

**Step 2: score** each candidate (at each allowed serving size `s` in {0.5, 1, 1.5, 2, 2.5, 3}), with nutrient values scaled by `s`:

`score = w_t × target_fit + w_c × cuisine_match − w_p × (total minutes / 60) − w_b × budget_ratio − w_r × repetition`

- `target_fit = −( |kcal − slot_kcal| / slot_kcal + |protein − slot_protein| / slot_protein ) / 2`, using only targets that exist.
- `cuisine_match`: +1 for a preferred cuisine at the strongest level, +0.5 for "like", 0 for neutral, −1 for "avoid" (a ranking penalty only).
- `budget_ratio = cost / slot budget share` when a budget is set, otherwise 0.
- `repetition` = times the recipe is already in the plan, plus 1 if it was in the same slot the previous day.
- Initial weights: `w_t = 1.0`, `w_c = 0.3`, `w_p = 0.2`, `w_b = 0.2`, `w_r = 0.5`.

**Step 3: choose.** Slots are filled day by day, in a fixed slot order. For each slot, the serving size that minimises `|kcal − slot_kcal|` is chosen (ties go to the smaller size), then the highest-scoring candidate wins; **ties are broken by recipe ID ascending**. The result is fully deterministic for the same inputs and the same catalogue.

**Step 4: totals and warnings.** Day totals are the sums of the meals. A `target_deviation` warning appears when day calories differ from the target by more than 10%, or protein is below 90% of its target (*initial*). If a hard filter leaves a slot with no candidate, no plan is created and the response is `infeasible` (section 7).

The generator does not claim to be optimal. A later version may use integer programming.

### 5.6 Substitutions and edits
- Substitution candidates for a meal are the recipes that pass the same hard filters for that slot (excluding the current one), scored as above against the slot's targets; the top 5 are returned with their nutrient differences from the current meal.
- Accepting a candidate replaces the meal, recalculates the meal and day totals and the grocery list, and marks the plan `edited`. The plan stays editable.
- A recipe added by hand that violates a **safety filter** is rejected (`violates_hard_constraint`); one that only conflicts with a preference or cap is accepted with a warning. Servings can be edited from 0.5 to 10.

### 5.7 Grocery list
- Ingredient quantities are scaled by `planned servings / recipe servings`.
- Quantities are summed only within a unit family: **mass** (g, kg), **volume** (ml, l, tsp, tbsp, cup) and **count** (piece). Different families for the same item stay on separate lines (no density conversion). Mass is shown in g (kg from 1,000 g), and volume in ml (l from 1,000 ml).
- Text-only ingredients are included and flagged. Items are grouped by food category and sorted deterministically.

### 5.8 Nutrition logging and comparison
- A log item records a food (in grams, or servings of its default serving) or a recipe (in servings), with a nutrient snapshot taken at logging time.
- For a day with a plan and at least one logged item, the comparison shows the difference between logged and planned calories and macros as amounts and percentages. A day is **"within range"** when calories differ by at most 10% (inclusive) from the planned total and protein is at least 90% of its target. A day with no logs is "not logged" and is excluded from averages; it is never treated as zero intake.

### 5.9 Insights
Insights are computed on demand from the user's data. Each one states its **time window**, **sample size** and **limitations**, has a minimum-data rule (for example, a strength trend needs at least 3 sessions containing the exercise within the window), and uses descriptive language only ("your estimated 1RM for squat rose from X to Y between these dates, based on N sets"). Causal wording is not allowed.

## 6. Data Model

The blueprint's schema is the base (all primary keys UUIDs, `created_at` and `updated_at`, foreign keys and constraints). This spec adds or changes the following.

| Table or field | Addition or change |
| --- | --- |
| `sessions` (new) | `id`, `user_id`, `token_hash`, `csrf_token_hash`, `created_at`, `expires_at`, `revoked_at`; server-side, revocable login sessions (decision D-03) |
| `user_profiles` | Adds `sex_for_estimate` (`male`, `female`, `unspecified`, optional), `adult_confirmed_at`, `needs_professional_guidance`, `calories_hidden`, `nutrition_paused`, `track_body_weight`, `weekly_session_target`, `currency_code`; `goal` is limited to `maintain` or `build_strength` |
| `user_food_constraints` | `constraint_type` is one of `allergy`, `diet_tag`, `excluded_ingredient`; allergy and diet-tag constraints are always hard |
| `foods` | Adds `state` (`raw`, `cooked`, `as_sold`), `approximate` flag, `allergens_verified` flag |
| `food_allergens` (new) | `food_id`, `allergen_code` (the 14 EU allergens: cereals containing gluten, crustaceans, eggs, fish, peanuts, soybeans, milk, tree nuts, celery, mustard, sesame, sulphites, lupin, molluscs) |
| `recipes` | Adds `cost_minor_per_serving`, `cost_currency`; recipe allergens are derived as the union of ingredient allergens |
| `recipe_diet_tags`, `recipe_meal_types` (new) | Normalised tags and the allowed meal slots |
| `catalog_versions` (new) | A version and content hash of the seed catalogue, recorded in each plan snapshot |
| `meal_plans` | `status` is `ok` or `edited`; `target_snapshot` also records constraints, weights and the catalogue version |

Everything else follows the blueprint: `ON DELETE CASCADE` for owned child rows, `RESTRICT` for shared catalogue rows referenced by history, `CHECK` constraints (reps > 0, load ≥ 0, RPE 1 to 10, positive servings, non-negative nutrients, valid date ranges), and indexes on `(user_id, started_at)`, `(user_id, consumed_at)`, `(user_id, start_date)` and all foreign keys.

## 7. API Contract

**Conventions**
- JSON over HTTPS. Decimals are strings. Timestamps are ISO 8601 in UTC. Dates are `YYYY-MM-DD` in the user's timezone.
- Identity comes from the session cookie only. Request bodies use strict schemas that **forbid unknown fields**, so a client-supplied `user_id` is rejected.
- A resource that belongs to someone else returns **404**, identical to a missing one (decision D-10).
- **Pagination:** `limit` (default 20, maximum 100) and an opaque `cursor`; responses are `{"items": [...], "next_cursor": "..." | null}`, ordered by a stable key.
- **Errors:** `{"error": {"code": "...", "message": "...", "details": {...}}}` with the status codes below.

| Status | Use |
| --- | --- |
| 400 | Malformed request |
| 401 | Not signed in, or invalid credentials |
| 403 | Signed in but not allowed (safety or role rules, `csrf_failed`, `tls_required`) |
| 404 | Missing or not owned |
| 409 | Conflict (`email_taken`, duplicate name, referenced catalogue row) |
| 413 | Body too large |
| 422 | Invalid values or domain rule violation |
| 429 | Rate limited, with `Retry-After` |
| 500 | Unexpected failure (no internal details leaked) |

**Endpoints** (the blueprint's outline, extended)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | Account and session |
| GET | `/api/auth/me` | The signed-in user |
| GET, PATCH | `/api/profile` | Profile, preferences and wellbeing settings |
| POST | `/api/profile/confirm-adult` | Record the adult confirmation |
| GET, POST | `/api/exercises` | Search; create a custom exercise |
| GET, POST | `/api/routines`; GET, PATCH, DELETE `/api/routines/{id}`; POST `/api/routines/{id}/duplicate`, `/api/routines/{id}/start` | Routines |
| GET, POST | `/api/workouts`; GET, PATCH, DELETE `/api/workouts/{id}` | Sessions |
| GET | `/api/analytics/strength` | Strength trends, PRs, volume |
| GET | `/api/analytics/consistency` | Sessions per week |
| GET, POST | `/api/foods`, `/api/recipes` | Catalogue search |
| GET, POST | `/api/nutrition/goals`; POST `/api/nutrition/goals/estimate` | Versioned targets; an estimate with assumptions |
| POST | `/api/meal-plans/generate` | Generate a plan (or an `infeasible` explanation) |
| GET, PATCH, DELETE | `/api/meal-plans/{id}` | Read, edit, delete |
| POST | `/api/meal-plans/{id}/substitutions` | `suggest` or `accept` |
| GET | `/api/meal-plans/{id}/grocery-list?from=&to=` | Grocery list for chosen days |
| GET, POST | `/api/nutrition/logs`; PATCH, DELETE `/api/nutrition/logs/{id}` | Intake logs |
| GET | `/api/analytics/nutrition` | Planned versus logged |
| GET | `/api/dashboard`, `/api/insights` | Combined dashboard and insights |
| GET | `/api/export` | Complete user data export |
| DELETE | `/api/account` | Delete the account (requires the password) |
| GET | `/api/health` | Liveness and database status |

**`POST /api/workouts`**

```json
{
  "started_at": "2026-10-15T11:30:00Z",
  "routine_id": null,
  "notes": "",
  "exercises": [
    {"exercise_id": "<uuid>", "order_index": 1, "sets": [
      {"set_number": 1, "reps": 5, "load_kg": "80.0", "rpe": "8.0",
       "is_warmup": false, "completed_at": "2026-10-15T11:40:00Z"}
    ]}
  ]
}
```

**`POST /api/meal-plans/generate`**

```json
{"start_date": "2026-10-19", "days": 7,
 "meal_slots": ["breakfast", "lunch", "dinner", "snack"],
 "max_minutes": 45, "daily_budget_minor": null}
```

A successful response has `"status": "ok"`, the plan with per-meal and per-day totals, a `warnings` list, the `disclaimer`, and an `explanation` object (constraints applied with the number of recipes each removed, the scoring weights, the `generation_version`, the catalogue version, and the share of approximate nutrient values). An **infeasible** request returns **200** with:

```json
{"status": "infeasible",
 "slot": "breakfast", "day": "2026-10-19",
 "filters": [{"filter": "allergy:peanuts", "removed": 6},
             {"filter": "diet:vegan", "removed": 9},
             {"filter": "max_minutes:15", "removed": 4}],
 "relaxable": ["max_minutes"],
 "message": "No breakfast recipe satisfies all of your safety filters and limits."}
```

No plan is stored. `relaxable` lists only non-safety limits (time, budget); an allergy or diet restriction is never suggested for removal.

## 8. Architecture

A **modular monolith** (decision D-01): simpler to build, test and explain than microservices, with clear module boundaries.

| Layer | Contents | Rule |
| --- | --- | --- |
| Routers (`app/api`) | FastAPI routers, dependencies, Pydantic schemas | Thin: parse, authorise, call a service, return |
| Services (`app/services`) | WorkoutService, StrengthAnalyticsService, NutritionService, PlanGeneratorService, GroceryListService, InsightService | Orchestrate use cases and transactions |
| Domain (`app/domain`) | Pure functions: units, e1RM, volume, PR detection, nutrient maths, targets, candidate filters, scoring, aggregation | No framework, database or clock imports; deterministic |
| Persistence (`app/models`, `app/repositories`) | SQLAlchemy models, repositories, Alembic migrations | All queries scoped by the authenticated user |
| Seed (`app/seed`) | Catalogue importers and validators | Idempotent |
| Frontend (`frontend/src`) | React and TypeScript pages, forms, charts | Types generated from the API's OpenAPI document (decision D-17) |

The blueprint's repository layout is kept (`backend/`, `frontend/`, `SPEC.md`, `README.md`, `DECISIONS.md`, `.env.example`, `docker-compose.yml`), with `docs/` for the ER diagram, architecture diagram, `DATA_LICENCES.md` and `test-plan.md`.

## 9. UI Requirements

| Screen | Contents |
| --- | --- |
| Sign in and register | Validation messages, rate-limit message |
| Profile and settings | Profile, units, timezone, wellbeing settings (S7), adult confirmation, professional-guidance flag, data export and deletion |
| Exercises | Search, filters, custom exercises |
| Routines | Create, edit, duplicate, start |
| Workout logger | Active session with fast set entry (a new set copies the previous set's values), warm-up toggle, RPE, notes |
| History | Paginated sessions with details |
| Strength | Per-exercise e1RM trend, PRs, volume, with a data-table alternative to each chart |
| Nutrition preferences and targets | Cuisines, diet tags, allergies, exclusions, limits, targets with assumptions |
| Plan | A 7-day grid, day detail with totals, target values and warnings, the explanation panel |
| Substitution | Suggested alternatives with nutrient differences |
| Grocery list | Grouped checklist |
| Nutrition log | Add and edit what was eaten |
| Dashboard | Consistency, strength, planned versus logged, insights with their limitations |

Every screen has **loading, empty and error states**. Forms show field-level errors linked to their fields with `aria-describedby`. All controls work by keyboard with a visible focus. The layout works at 360 pixels wide, because the logger is used in the gym. Colour is never the only carrier of meaning, and charts have a text or table alternative.

## 10. Security

| ID | Requirement |
| --- | --- |
| **SEC1 Passwords** | Hashed with **Argon2id**; minimum 12 and maximum 128 characters; plaintext never stored, logged or returned. |
| **SEC2 Sessions** | Server-side, revocable sessions in an `HttpOnly`, `SameSite=Lax` cookie that is `Secure` whenever served over TLS; logout and account deletion revoke them. |
| **SEC3 CSRF** | Every non-GET request must carry a CSRF token (double-submit) or fail with `csrf_failed`. |
| **SEC4 Authorisation** | Ownership is enforced in every service and repository call, never only in the UI. Foreign resources return 404. |
| **SEC5 Authentication errors** | A wrong email and a wrong password give the identical response. A dummy hash is checked for unknown emails so timing does not reveal them. |
| **SEC6 Rate limiting** | At most 5 failed logins per account and per IP in 15 minutes, then 429 with `Retry-After`. |
| **SEC7 TLS for credentials** | Credentials are accepted from non-localhost clients only over TLS (`tls_required`). Forwarded-protocol headers are trusted only from the configured reverse proxy. |
| **SEC8 Input validation** | Strict schemas, forbidden extra fields, range checks, a 1 MB body limit, and parameterised queries only. |
| **SEC9 Headers and CORS** | A Content-Security-Policy, `X-Content-Type-Options`, `Referrer-Policy`, frame protection, and CORS limited to the configured origin. |
| **SEC10 Secrets** | Only in environment variables; `.env` is never committed; the application refuses to start in production mode with missing or placeholder secrets. |
| **SEC11 Dependencies** | `pip-audit` and `npm audit` are run before release and their results recorded. |
| **SEC12 Logging** | Structured logs with request IDs; no passwords, tokens, session IDs or full email addresses. |

## 11. Production Deployment

The project must run as a deployed service. "Deployed" means: built into container images and run as long-lived services that you open in a browser on your own computer or from another device on the same network (intranet). It stores personal fitness and food data, so credentials and sessions must not cross a network in the clear.

| ID | Requirement |
| --- | --- |
| **D1 Services** | Docker Compose runs `db` (PostgreSQL with a named volume), `backend` (FastAPI under a production server, not auto-reload), and `frontend` (the built React files served by nginx, which proxies `/api` to the backend). |
| **D2 Non-root, pinned** | Application containers run as a non-root user; base images and dependencies are pinned. |
| **D3 One command** | After `cp .env.example .env` and setting the secrets, `docker compose up -d` builds and starts everything, applies migrations, and serves the UI at `http://localhost:8080`. |
| **D4 Seed and demo data** | `docker compose run --rm backend python -m app.seed` loads the reviewed catalogue; `python -m app.demo_user` creates a clearly labelled **synthetic** demo account with 12 weeks of workouts and nutrition logs for the demonstration. |
| **D5 Health and restart** | `/api/health` reports the database status; all services have health checks and `restart: unless-stopped`. |
| **D6 HTTPS on the network** | For use from other devices, a TLS reverse proxy (for example Caddy or nginx) serves `https://<LAN-IP>:8443`, using a certificate from a private certificate authority you create (a tool such as mkcert can do this) that your devices trust. Plain-HTTP credentials from non-localhost clients are refused (SEC7). |
| **D7 Backups** | A documented `pg_dump` backup and restore procedure, verified by restoring into a clean database. |
| **D8 Optional public host** | A public deployment on a free host is optional and must run with registration limited and only synthetic data. |

## 12. Functional Requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Accounts and profile: register, sign in, update the profile, and access only your own records. |
| FR-02 | Exercise catalogue: search, instructions, equipment, primary muscle group; custom exercises. |
| FR-03 | Workout logging: sessions with exercises and sets (reps, load, optional RPE and rest, warm-up flag). |
| FR-04 | Routines: create, edit, duplicate, and start a workout from a routine. |
| FR-05 | Strength metrics: personal records, estimated 1RM, volume and trends per exercise. |
| FR-06 | Nutrition profile: multiple cuisines, diet tags, allergies, exclusions, budget and time limits. |
| FR-07 | Nutrition targets: editable, versioned, with optional transparent estimates and the safety rules S2 to S6. |
| FR-08 | Plan generator: deterministic, explainable, editable 7-day plans, with `infeasible` explanations. |
| FR-09 | Nutrient calculation: meal and day totals from quantities and per-100-g data. |
| FR-10 | Substitutions with recalculated totals and grocery list. |
| FR-11 | Unit-aware grocery list over selected days. |
| FR-12 | Nutrition logging and planned versus actual comparison. |
| FR-13 | Combined dashboard of consistency, strength, nutrition and plan match. |
| FR-14 | Descriptive, evidence-grounded insights with windows, sample sizes and limitations. |
| FR-15 | Data controls: edit and delete records, export all data, and delete the account. |
| FR-16 | The safety and wellbeing rules S1 to S10 (section 3). |
| FR-17 | The security requirements SEC1 to SEC12 (section 10). |
| FR-18 | A reviewed seed catalogue with provenance, validators and a synthetic demo account. |
| FR-19 | Production deployment meeting section 11. |
| FR-20 | Documentation: README, ER diagram, architecture diagram, `DECISIONS.md`, `DATA_LICENCES.md`, test plan and known limitations. |

## 13. Acceptance Criteria

Dates and clocks in tests are injected, so results are deterministic.

### Accounts and security
- [ ] **AC-01** (SEC1) Registering stores an Argon2id hash (the stored value starts with `$argon2id$`), never returns or logs the password, and returns 409 `email_taken` for a duplicate email, compared case-insensitively (`A@x.com` and `a@x.com` conflict).
- [ ] **AC-02** (SEC1) A password of 11 characters is rejected with 422; 12 and 128 characters are accepted; 129 is rejected.
- [ ] **AC-03** (SEC2, SEC5) Login sets an `HttpOnly`, `SameSite=Lax` cookie (and `Secure` over TLS); a wrong email and a wrong password return the same status and body (`invalid_credentials`).
- [ ] **AC-04** (SEC6) The 6th failed login within 15 minutes for one account returns 429 with `Retry-After`; after the window passes (injected clock) a correct login succeeds.
- [ ] **AC-05** (SEC2) After logout, the old session cookie returns 401 on every endpoint.
- [ ] **AC-06** (SEC3) A POST, PATCH or DELETE without a valid CSRF token returns 403 `csrf_failed`; GET requests are unaffected.
- [ ] **AC-07** (SEC7) A login over plain HTTP from a non-localhost client returns 403 `tls_required`; over TLS, or from localhost, it works; a forged forwarded-protocol header from an untrusted client is ignored.
- [ ] **AC-08** (SEC4) *Ownership matrix.* For every user-owned endpoint (derived automatically from the route table), user B requesting, changing or deleting user A's resource by ID gets a 404 identical to a missing ID, list endpoints never include A's items, and A's data is unchanged in the database.
- [ ] **AC-09** (SEC8) A request body containing `user_id` (or any unknown field) is rejected with 422.
- [ ] **AC-10** (SEC8) The string `'; DROP TABLE users;--` saved in a note is stored and returned literally, and all tables remain intact.
- [ ] **AC-11** (SEC9) Responses carry the Content-Security-Policy, `X-Content-Type-Options`, `Referrer-Policy` and frame-protection headers; CORS allows only the configured origin.
- [ ] **AC-12** (SEC10) A script finds no secret patterns in tracked files and no tracked `.env`; in production mode the application refuses to start with a missing secret or one equal to the `.env.example` placeholder.
- [ ] **AC-13** (SEC8) A request body above 1 MB returns 413.
- [ ] **AC-14** (SEC11) `pip-audit` and `npm audit` show no known high or critical vulnerabilities at release; the results are recorded.

### Profile, units and safety
- [ ] **AC-15** (FR-01) Profile validation rejects, with 422 and field names: height outside 50 to 260 cm, weight outside 20 to 400 kg, an invalid IANA timezone, and units other than `kg` or `lb`.
- [ ] **AC-16** (5.1) 100 lb converts to 45.359237 kg exactly, 1 kg to 2.2046226218 lb, a round trip returns the original within 1e-9, and storage is always in kg.
- [ ] **AC-17** (S2) Nutrition endpoints return 403 `adult_confirmation_required` until the user confirms. With a birth date of 2008-10-16, nutrition planning is blocked (`nutrition_not_available_for_minors`) on 2026-10-15 (age 17) and allowed on 2026-10-16 (age 18); workout endpoints work in both cases.
- [ ] **AC-18** (S3) With `needs_professional_guidance` on, the estimate endpoint returns 409 `manual_targets_required`, manual targets are accepted, and responses carry `requires_professional_guidance: true`.
- [ ] **AC-19** (S4) For male, 80 kg, 180 cm, age 25, moderate activity, `build_strength`: BMR 1,805, TDEE 2,797.75, plus 5% = 2,937.64, rounded to **2,940 kcal**; protein **128 g** (1.6 × 80); fat **82 g** (25% of 2,940 kcal ÷ 9); carbohydrate **423 g** (the remaining 1,693 kcal ÷ 4). The response lists the formula, activity factor, goal adjustment, protein and fat assumptions.
- [ ] **AC-20** (S4) The same inputs with `sex_for_estimate = unspecified` use `s = −78`: BMR 1,722, TDEE 2,669.1, plus 5% = 2,802.56, rounded to **2,800 kcal**, and the assumption is shown.
- [ ] **AC-21** (S5) For female, 45 kg, 160 cm, age 30, sedentary, `maintain` (BMR 1,139, TDEE 1,366.8), the estimate endpoint returns `estimate_below_floor`, saves no target, and tells the user to enter a target manually or seek guidance.
- [ ] **AC-22** (S5) A manual target of 1,400 kcal is saved with a `below_recommended_minimum` warning; a manual target of 1,100 kcal is saved, but plan generation returns 422 `target_below_minimum`.
- [ ] **AC-23** (5.4) Changing a target creates a new `nutrition_goals` row; the active target on a date is the latest row with `effective_from` on or before it; earlier rows and existing plan snapshots are unchanged.
- [ ] **AC-24** (S7) With `calories_hidden` on, no screen in the end-to-end suite contains the words "kcal" or "calorie", protein and other macros are still shown, and plan generation still works.
- [ ] **AC-25** (S7) With `nutrition_paused` on, nutrition endpoints return 403 `nutrition_paused`, workout features work, no data is deleted, and switching it off restores access.
- [ ] **AC-26** (S7) With `track_body_weight` off, no screen or endpoint asks for or charts body weight; no workout or nutrition flow requires it.
- [ ] **AC-27** (S8) A test scanning all UI strings and insight templates finds none of the banned words (`failed`, `cheat`, `bad`, `guilt`, `streak lost`, `caused`, `because of`).
- [ ] **AC-28** (S1) Every plan, target and insight screen shows the informational notice, and every plan response includes a `disclaimer` field.

### Exercises, workouts and routines
- [ ] **AC-29** (FR-02) Searching `squat` returns exercises whose name contains it (case-insensitive), filters by muscle and equipment work, results are paginated, and a custom exercise is visible only to its owner.
- [ ] **AC-30** (FR-02) A custom exercise name must be unique per owner (case-insensitive), otherwise 409; seed exercises cannot be edited or deleted by users.
- [ ] **AC-31** (FR-03) Saving a workout with exercises and sets persists the session and every child row, and it appears in history in the saved order.
- [ ] **AC-32** (FR-03) Validation: reps 0 and load −1 are rejected; load 0 is accepted; RPE 11 is rejected, 7.5 accepted, and 7.3 rejected (steps of 0.5); duplicate set numbers are rejected; a set `completed_at` earlier than the session start is rejected.
- [ ] **AC-33** (NFR) *Atomicity.* A workout with three valid sets and one invalid set returns 422 and leaves no session, exercise or set rows; an injected database failure midway rolls everything back.
- [ ] **AC-34** (FR-15) Editing a workout replaces its sets and analytics update; deleting it removes its children and no other user's data.
- [ ] **AC-35** (FR-04) A routine stores ordered exercises with target sets and rep ranges (`rep_min ≤ rep_max`); duplicating it makes an independent copy; starting a workout from it pre-fills exercises and targets with no sets logged and records the `routine_id`.
- [ ] **AC-36** (5.1) For `Asia/Kolkata`, sets at `2026-10-15T18:29:59Z` and `2026-10-15T18:30:00Z` fall on 15 October and 16 October (local) respectively, and per-day counts follow.
- [ ] **AC-37** (7) History pagination returns at most `limit` items in a stable order, and `next_cursor` continues without duplicates or gaps even when new sessions are inserted between page requests.
- [ ] **AC-38** (NFR) With 10,000 sessions, the history query plan uses the `(user_id, started_at)` index.

### Strength analytics
- [ ] **AC-39** (5.2) e1RM: 80 kg × 5 gives **93.33** (displayed 93.3, labelled estimated); 100 kg × 1 gives **100.0**; 60 kg × 12 gives **84.0**; 13 reps returns `null` with `rep_range`; warm-up sets are excluded.
- [ ] **AC-40** (5.2) Volume for working sets 80 × 5, 80 × 5, 80 × 4 is **1,120 kg**; a 40 × 10 warm-up is excluded.
- [ ] **AC-41** (5.2) For sets 80 × 5, 85 × 5, 90 × 3 in order: the first is the baseline, 85 × 5 (e1RM 99.17) is a PR, and 90 × 3 (e1RM 99.0) is not; an equal e1RM is not a PR; deleting the PR set recomputes PRs.
- [ ] **AC-42** (FR-05) The trend endpoint returns, per exercise, the best e1RM per session date (user timezone) within the window, converts units for lb users, and returns an empty list with 200 when there is no data.
- [ ] **AC-43** (NFR) e1RM uses exact decimals: 82.5 kg × 3 reps gives exactly 90.75.
- [ ] **AC-44** (5.2) Sessions on a Monday, Wednesday and Saturday give 3 for that week, a week with none gives 0, and a session with only warm-up sets is not counted.

### Catalogue and nutrient maths
- [ ] **AC-45** (FR-09) 150 g of a food with 20 g protein per 100 g gives exactly 30 g protein.
- [ ] **AC-46** (5.3) An ingredient of 200 g with `edible_weight_g` 150 uses 150 g in the calculation.
- [ ] **AC-47** (5.3) *Fixture recipe.* Fixture foods (test fixtures only, per 100 g): F1 has 150 kcal, 25 g protein, 0 g carbohydrate, 5 g fat; F2 has 350 kcal, 8 g protein, 75 g carbohydrate, 1 g fat. A recipe of 200 g F1 and 100 g F2 with 2 servings totals 650 kcal, 58 g protein, 75 g carbohydrate, 11 g fat, so **per serving 325 kcal, 29 g protein, 37.5 g carbohydrate, 5.5 g fat**.
- [ ] **AC-48** (NFR) The database rejects a negative nutrient, a non-positive serving, and an invalid date range with its own `CHECK` constraints.
- [ ] **AC-49** (DL1) Seed validation fails if any food lacks `data_source`, serving basis, state or `verified_at`; foods flagged `approximate` are labelled as such in API responses.
- [ ] **AC-50** (DL1) For every seed food not flagged as an exception, `|kcal − (4 × protein + 4 × carbohydrate + 9 × fat)|` is at most the larger of 20 kcal and 15% of the food's kcal.
- [ ] **AC-51** (FR-18) The seed command is idempotent (running it twice changes no counts) and loads 30 to 50 exercises, 40 to 60 foods and 15 to 25 recipes covering at least 4 cuisines, each recipe with at least 2 ingredients, valid servings and non-negative times.
- [ ] **AC-52** (S9) Every seed food has an allergen status; a recipe's allergens are the union of its ingredients' allergens; a recipe with a text-only ingredient reports its allergen data as incomplete.
- [ ] **AC-53** (FR-06) Catalogue search filters by cuisine, diet tag and maximum time, with pagination.
- [ ] **AC-54** (5.3) After a food's nutrient value is corrected in the catalogue, existing plan and log snapshots keep the old values, and new entries use the new ones.
- [ ] **AC-55** (NFR) Deleting a food referenced by history returns 409.

### Plan generation
- [ ] **AC-56** (5.5) The same inputs and catalogue give identical plans (compared on content), over 20 runs.
- [ ] **AC-57** (S9) *Allergen property test.* For each of the 14 allergens and 100 random preference sets, a generated plan contains no recipe or ingredient carrying that allergen.
- [ ] **AC-58** (S9) With any allergy set and `exclude_unverified_allergens` on, no plan includes a recipe with a text-only ingredient or an ingredient with unverified allergen data.
- [ ] **AC-59** (5.5) A vegan user's plan contains only vegan recipes; the same holds for each diet tag; an excluded ingredient never appears (case-insensitive, by name and by food).
- [ ] **AC-60** (5.5) With a 30-minute cap, no selected recipe has `prep_minutes + cook_minutes` above 30; with a daily budget, no day's total cost exceeds it, or the result is `infeasible`.
- [ ] **AC-61** (5.5) With preferred cuisines set and enough candidates, at least 70% of planned meals (*initial*) come from preferred cuisines; if only "avoid" cuisines can fill a slot, the plan is still produced with a `cuisine_preference_unmet` warning.
- [ ] **AC-62** (7) When the hard filters leave a slot with no candidates, the response is `infeasible` with the slot, the day and a per-filter count of recipes removed; no plan row is stored; `relaxable` never contains an allergy or diet restriction.
- [ ] **AC-63** (5.5) *Scoring example.* Slot target 700 kcal and 40 g protein; a candidate at 650 kcal and 35 g protein, a preferred cuisine, total time 20 minutes, no budget, no repetition, `s = 1`: `target_fit = −(50/700 + 5/40)/2 = −0.09821`, `score = −0.09821 + 0.3 − 0.2 × (20/60) =` **0.1351**.
- [ ] **AC-64** (5.5) A recipe of 400 kcal per serving against a 700 kcal slot: sizes 1.5 (600) and 2 (800) tie at a deviation of 100, so **1.5** is chosen; 1.75 is not an allowed size.
- [ ] **AC-65** (5.5) Candidates with equal scores are ordered by recipe ID ascending, identically across runs.
- [ ] **AC-66** (5.5) With at least 10 eligible lunches, no recipe appears more than twice in 7 days in the same slot, and none on consecutive days for that slot.
- [ ] **AC-67** (5.5) A day whose calories differ from the target by more than 10% gets a `target_deviation` warning with the values; protein below 90% of target warns; a missing target produces no warning for it; day totals always equal the sum of the meals.
- [ ] **AC-68** (5.5) The plan's `target_snapshot` records targets, constraints, weights and catalogue version; later profile changes do not alter an existing plan or its totals.
- [ ] **AC-69** (FR-08) Generation with no targets returns 422 `targets_required`; with the safety rules unmet it returns the matching 403 or 422 (AC-17, AC-22, AC-25).
- [ ] **AC-70** (NFR) *(initial targets)* Generation takes at most **2 seconds at p95** with the 25-recipe seed catalogue, and at most **5 seconds** with a generated catalogue of 500 recipes.
- [ ] **AC-71** (NFR) Saving a plan is transactional: a failure leaves no partial plan.
- [ ] **AC-72** (FR-08) Every plan response includes the explanation block: constraints applied with counts removed, scoring weights, `generation_version`, catalogue version, the share of approximate nutrient values, and the statement that the plan is not guaranteed optimal.

### Substitutions, edits and grocery list
- [ ] **AC-73** (FR-10) Substitution suggestions pass the same hard filters for the slot, exclude the current recipe, are ordered by score, number at most 5, and each shows its nutrient differences from the current meal.
- [ ] **AC-74** (FR-10) Accepting a substitution updates the meal, the day totals, the grocery list and the plan status (`edited`), and the totals equal a from-scratch recomputation.
- [ ] **AC-75** (5.6) A manually added recipe that violates an allergy is rejected with `violates_hard_constraint`; one that only exceeds a time cap or is of an unwanted cuisine is accepted with a warning.
- [ ] **AC-76** (5.6) Changing servings from 1 to 2 doubles the meal's nutrients; 0, −1 and 11 are rejected; 0.5 and 10 are accepted.
- [ ] **AC-77** (5.7) `250 g + 0.5 kg` aggregates to **750 g**; `2 tbsp + 1 tsp` to **35 ml**; `1 cup + 100 ml` to **340 ml**; 1,200 g displays as **1.2 kg**.
- [ ] **AC-78** (5.7) `2 piece` of onion and `300 g` of onion stay on separate lines, and so do mass and volume amounts of the same food.
- [ ] **AC-79** (5.7) A 4-serving recipe with 400 g of an ingredient, planned at 1.5 servings, contributes **150 g**.
- [ ] **AC-80** (FR-11) A grocery list for days 2 to 4 includes only those days' meals; an empty selection returns an empty list with 200.
- [ ] **AC-81** (FR-11) Items are grouped by food category and sorted deterministically; text-only ingredients are included and flagged.

### Logging, dashboard and insights
- [ ] **AC-82** (FR-12) Logging by food (grams or servings of the default serving) or by recipe (servings) stores the quantity and a nutrient snapshot; editing or deleting a log item updates all totals.
- [ ] **AC-83** (5.8) For a planned day of 2,900 kcal and 125 g protein and logs totalling 2,610 kcal and 140 g protein: the difference is **−290 kcal (−10.0%)** and **+15 g (+12.0%)**, the day is "within range" (the 10% limit is inclusive), and the labels are neutral.
- [ ] **AC-84** (5.8) A day with no logs is "not logged" and excluded from averages, never shown as zero intake; `consumed_at` is assigned to days in the user's timezone.
- [ ] **AC-85** (FR-13) The dashboard returns weekly sessions, weekly volume, PR count and planned versus logged summaries for a window, and a new user gets zero values and empty states with status 200.
- [ ] **AC-86** (5.9) Every insight carries `window`, `n`, `limitations` and `evidence`; with fewer than 3 sessions of an exercise in the window, no trend insight is produced and the response says there is not enough data.
- [ ] **AC-87** (5.9, S8) Insight templates contain no causal wording (checked with the banned-word test).

### Data controls
- [ ] **AC-88** (FR-15) The export contains every record of every user-owned table for the signed-in user and no one else's, validates against a published JSON schema, and its record counts match the database.
- [ ] **AC-89** (FR-15) Deleting the account (which requires the password) removes all rows for that user from every user-owned table (verified by scanning every table), revokes sessions, and leaves the shared catalogue intact.

### Interface and accessibility
- [ ] **AC-90** (9) Every screen in section 9 has loading, empty and error states, and field errors are linked to their fields with `aria-describedby`.
- [ ] **AC-91** (9) A keyboard-only end-to-end test logs a complete workout; every interactive element shows a visible focus.
- [ ] **AC-92** (9) An automated accessibility scan (axe) reports zero serious or critical violations on every main page.
- [ ] **AC-93** (9) Every chart has a text summary or a data-table alternative, verified by a test.
- [ ] **AC-94** (9) At 360 × 740 pixels, no main page scrolls horizontally.
- [ ] **AC-95** (9) *(initial target)* Adding a set in the logger takes at most 3 interactions, with the previous set's values copied by default.
- [ ] **AC-96** (5.1) Switching units between kg and lb applies consistently across screens and API responses, with lb shown to 1 decimal place.

### Quality and architecture
- [ ] **AC-97** (NFR) `alembic upgrade head` builds the schema from an empty database, `alembic downgrade base` works, and `alembic check` reports no drift between models and migrations.
- [ ] **AC-98** (8) An import-linter or equivalent test confirms that `app/domain` imports no framework, database or clock module and that routers contain no business rules.
- [ ] **AC-99** (8) The frontend's API types are generated from the backend's OpenAPI document, and CI fails if they are out of date.
- [ ] **AC-100** (NFR) *(initial targets)* Line coverage is at least **90%** for the domain and services and **70%** for the frontend.
- [ ] **AC-101** (NFR) CI runs lint, type checks (strict mypy and `tsc`), unit, database, API, frontend and end-to-end tests, and fails on any failure.
- [ ] **AC-102** (NFR) Regression fixtures (fixed sets and fixture foods) reproduce the expected metrics of AC-39 to AC-47.
- [ ] **AC-103** (NFR) *(initial targets)* With the demo dataset (2 years, about 500 sessions, 10,000 sets), history and analytics endpoints take at most **300 ms at p95** and the dashboard at most **500 ms**.
- [ ] **AC-104** (SEC12) A canary test shows that no password, token, session ID or full email address appears in the logs.

### Deployment and documentation
- [ ] **AC-105** (D3) From a fresh clone, `cp .env.example .env` and `docker compose up -d` start every service, apply migrations, and serve the UI at `http://localhost:8080`.
- [ ] **AC-106** (D4) The seed command and the demo-user command work, the demo account is labelled synthetic, and the full demo journey runs in the browser.
- [ ] **AC-107** (D5) `/api/health` returns 200 with the database status; all containers report healthy, restart after a killed process, and run as non-root.
- [ ] **AC-108** (D7) Data survives `docker compose down` and `up`; a `pg_dump` backup restores into a clean database with identical row counts.
- [ ] **AC-109** (D6) Through the TLS proxy at `https://<LAN-IP>:8443`, a device that trusts your private certificate authority loads the app without a warning; TLS 1.2 or higher only; plain-HTTP login from a non-localhost client is refused.
- [ ] **AC-110** (D6) From a second device on the same network, sign in and log a workout. This is a manual check: record the date and result in the README.
- [ ] **AC-111** (SEC10) `.env.example` lists every variable, and a test confirms that the application's required variables all appear in it.
- [ ] **AC-112** The end-to-end journey passes in CI against the Compose stack: sign in, log a workout, view the strength trend, set preferences, generate a plan, substitute a meal, view the grocery list, log intake, and open the dashboard.
- [ ] **AC-113** *(Optional)* (D8) A public deployment runs with synthetic data only and limited registration.
- [ ] **AC-114** (FR-20) The README documents setup, environment variables, seed data, migrations, tests, the demo steps, and known limitations.
- [ ] **AC-115** (FR-20) `docs/` contains the ER diagram, the architecture diagram, `DATA_LICENCES.md` with each data source and its licence, and `test-plan.md` mapping every acceptance criterion to a test or manual check.
- [ ] **AC-116** (FR-20) `DECISIONS.md` mirrors the Decisions Log, and every safety threshold in section 3 has a cited source or an explicit note that it is a placeholder under review.
- [ ] **AC-117** (S1, FR-20) No page, API field or document describes any estimate as medically authoritative or promises an outcome.
- [ ] **AC-118** (FR-20) The README states the limitations of v1: self-declared adult confirmation, no email verification or password reset, approximate nutrient data, no density conversion in the grocery list, and the greedy planner's lack of optimality.

## 14. Traceability to the Blueprint's Functional Requirements

| Blueprint | Covered by |
| --- | --- |
| FR-01 Accounts and profile | AC-01 to AC-09, AC-15 to AC-17 |
| FR-02 Exercise catalogue | AC-29, AC-30 |
| FR-03 Workout logging | AC-31 to AC-34, AC-36 to AC-38 |
| FR-04 Routines | AC-35 |
| FR-05 Strength metrics | AC-39 to AC-44 |
| FR-06 Nutrition profile | AC-53, AC-57 to AC-61 |
| FR-07 Nutrition targets | AC-18 to AC-23 |
| FR-08 Diet-plan generator | AC-56 to AC-72 |
| FR-09 Nutrient calculation | AC-45 to AC-47 |
| FR-10 Substitutions | AC-73 to AC-76 |
| FR-11 Grocery list | AC-77 to AC-81 |
| FR-12 Nutrition logging | AC-82 to AC-84 |
| FR-13 Combined dashboard | AC-85 |
| FR-14 Insights | AC-86, AC-87 |
| FR-15 Data controls | AC-34, AC-88, AC-89 |

## 15. Non-Functional Requirements

| Area | Requirement |
| --- | --- |
| Correctness | Exact decimals for all calculations; one place for each formula; formulas live in `app/domain` |
| Reliability | Multi-row writes (workouts, plans, logs) run in transactions |
| Performance | Paginated history, the indexes in section 6, and the targets in AC-70 and AC-103 |
| Maintainability | Thin routers, services for rules, repositories for queries, enforced by AC-98 |
| Explainability | Every plan exposes its targets, constraints, scoring weights and data provenance |
| Accessibility | Section 9 and AC-90 to AC-94 |
| Privacy | Collect only what is needed; export and delete (S10, FR-15) |
| Testability | Injected clock, seeded fixtures, deterministic planner |

## 16. Testing Strategy

| Layer | What it checks | Tooling |
| --- | --- | --- |
| Unit (domain) | Units, e1RM, volume, PRs, nutrient maths, targets, filters, scoring, aggregation, with the worked numbers above | pytest |
| Property | Allergen exclusion, totals equal sums, deterministic plans, ownership matrix | pytest with Hypothesis |
| Database | Constraints, cascades, restrictions, transactions, migrations, index use | pytest against a real PostgreSQL (a Compose service), never SQLite |
| API | Authentication, CSRF, validation, ownership, errors, pagination | pytest with HTTPX or TestClient |
| Frontend | Forms, validation messages, states, substitution flow, chart alternatives | Vitest and Testing Library |
| End to end | The full journey, keyboard-only logging, 360-pixel layout, accessibility scan, hidden-calories mode | Playwright and axe |
| Safety | Section 3 rules, banned-word scan, minors and floor behaviour | pytest and the end-to-end suite |
| Quality gates | Lint, type checks, coverage, OpenAPI type freshness, secret scan, dependency audit | CI |
| Deployment | Container build, health, restart, persistence, backup and restore, TLS | Docker, a smoke script, a manual second-device check |

Expected values come from the calculations written in the acceptance criteria, not from copying the application's output.

## 17. Build Order

Build in this order, because each step depends on the one before it. A step is done when its acceptance criteria pass. There are no time estimates; go as fast as the tests allow.

| Step | Build | Acceptance criteria |
| --- | --- | --- |
| 1 | Repo and tooling setup, CI skeleton, ER diagram, and a walking-skeleton Compose stack (database, a backend with `/api/health`, a placeholder frontend) | AC-97 (start), AC-105 (skeleton) |
| 2 | The pure domain functions: units, e1RM, volume, PRs, nutrient maths, targets, aggregation, scoring, with their unit tests | AC-16, AC-39 to AC-41, AC-43, AC-45 to AC-47, AC-63, AC-64, AC-77 to AC-79, AC-19 to AC-21 (maths) |
| 3 | Database models and migrations, authentication, sessions, CSRF, rate limiting, TLS rule, and the ownership-test harness | AC-01 to AC-13, AC-15, AC-97, AC-98, AC-104 |
| 4 | Catalogue and seed: exercises, foods, recipes, provenance, allergens, validators | AC-48 to AC-55 |
| 5 | Workouts and routines: API and UI, history, pagination, edit and delete, the logger | AC-29 to AC-38, AC-90 to AC-96 (for these screens) |
| 6 | Strength analytics and charts | AC-40 to AC-42, AC-44, AC-93 |
| 7 | Nutrition profile, targets and the safety rules, with the settings UI | AC-17 to AC-28 |
| 8 | The plan generator, with `infeasible` explanations and the plan UI | AC-56 to AC-72 |
| 9 | Substitutions, manual edits, and the grocery list | AC-73 to AC-81 |
| 10 | Nutrition logging, planned versus actual, dashboard and insights | AC-82 to AC-87 |
| 11 | Data export and account deletion, accessibility and hardening, performance work | AC-88, AC-89, AC-91, AC-92, AC-94, AC-99 to AC-103 |
| 12 | Production deployment: Compose, the TLS proxy, backups, demo data, the end-to-end journey in CI, the dependency audit, and all documentation | AC-14, AC-105 to AC-118 |
| 13 | Stretch: integer-programming planner, association insight, rest timers, custom foods, public demo | None required |

Steps 5 and 6 (training) are independent of steps 7 to 9 (nutrition) once step 4 is done, so they can be built in parallel. The frontend of each step can start as soon as that step's API contract is fixed in the OpenAPI document. Keep the Compose stack from step 1 working throughout.

**If you need to cut scope, cut in this order:** all of step 13, the optional public host, association insights, and the 500-recipe performance test. Never cut the ownership tests, the allergen tests, the safety rules S1 to S10, the nutrient-maths tests, or the transactions.

## 18. Decisions Log

| ID | Date | Decision | Alternatives | Why |
| --- | --- | --- | --- | --- |
| D-01 | 2026-10-16 | A modular monolith | Microservices | Less operational complexity, same clean boundaries, easier to test and explain |
| D-02 | 2026-10-16 | React and TypeScript, FastAPI, PostgreSQL, SQLAlchemy 2 and Alembic, as the blueprint recommends | Other stacks | Typed end to end, relational constraints and transactions suit this data |
| D-03 | 2026-10-16 | Server-side revocable sessions in an `HttpOnly` cookie, with a CSRF token | Stateless JWTs | Logout and account deletion can truly revoke access, and cookies are not readable by scripts |
| D-04 | 2026-10-16 | Argon2id password hashing | bcrypt | Memory-hard, and current guidance favours it (check the parameters against current guidance) |
| D-05 | 2026-10-16 | Decimals travel as strings in the API | JSON numbers | No floating-point surprises in nutrient and load values |
| D-06 | 2026-10-16 | A deterministic greedy planner with an explicit scoring formula | Integer programming; machine learning | Reproducible, explainable and testable; optimisation is a later step once data quality is reliable |
| D-07 | 2026-10-16 | Allergens are hard filters, and unverified allergen data is excluded by default | Treat unknown as safe | Catalogue data can be incomplete, and a wrong inclusion is worse than a smaller plan |
| D-08 | 2026-10-16 | Time and budget are hard caps only when the user sets them; cuisine and variety only rank | Treat everything as ranking | Matches the blueprint's "filters" while keeping preferences flexible |
| D-09 | 2026-10-16 | Nutrient snapshots on plan and log items, and a catalogue version in each plan | Recompute from the live catalogue | Later corrections never silently rewrite history |
| D-10 | 2026-10-16 | A foreign resource returns 404, the same as a missing one | 403 | Does not reveal that the record exists |
| D-11 | 2026-10-16 | No weight-loss or deficit goals in v1; only `maintain` and `build_strength` | Include a cut goal | The product is strength-focused, and deficit features carry more risk than this project can responsibly manage |
| D-12 | 2026-10-16 | A self-declared adult confirmation, plus a birth-date check when given | Collect a birth date from everyone | Collects less sensitive data; the limitation is documented |
| D-13 | 2026-10-16 | Cursor pagination | Offset pagination | Stable under inserts, with no duplicates or gaps |
| D-14 | 2026-10-16 | Epley e1RM for 1 to 12 reps, with `e1RM = load` at 1 rep | Brzycki; any rep count | Simple, well known, and the rep range limits the error |
| D-15 | 2026-10-16 | `1 cup = 240 ml`, `1 tbsp = 15 ml`, `1 tsp = 5 ml`, with no mass-volume conversion | Regional cup sizes; density tables | Predictable, and avoids inventing densities |
| D-16 | 2026-10-16 | Credentials only over TLS beyond localhost, with a private certificate authority for the network | Plain HTTP on the network | Passwords and sessions must not be readable on the network |
| D-17 | 2026-10-16 | Frontend API types generated from the OpenAPI document | Hand-written types | Front and back end cannot drift apart without CI failing |
| D-18 | 2026-10-16 | Neutral wording, a hide-calories option, a pause option, and opt-in weight tracking | Always show everything | Reduces harm for users for whom numbers are unhelpful |
| D-19 | 2026-10-16 | A small reviewed catalogue with recorded sources and licences | Import a very large database | Quality, licence clarity and testability before scale |
| D-20 | 2026-10-16 | An automated layering check (domain imports nothing from frameworks) | Convention only | Keeps the rules pure and testable |
| D-27 | 2026-10-19 | New accounts start with "beef" in excluded ingredients (`DEFAULT_EXCLUDED_INGREDIENTS`); users can remove it | Remove beef from the catalogue; swap beef for chicken or mutton | India-focused app where many users avoid beef; keeps the catalogue intact and the choice with the user |

## 19. Open Questions

- [ ] Which data sources will you use for foods (and for Indian or other regional foods), and what are their licences (DL2)?
- [ ] Which cuisines will the seed recipes cover, and who will review the allergen tagging?
- [ ] Which sources will you cite for the Mifflin–St Jeor equation, the activity factors, the 1.6 g per kg protein default and the 1,500 and 1,200 kcal thresholds?
- [ ] Do you want the optional estimate at all, or manual targets only?
- [ ] Which currency and units should be the defaults?
- [ ] Should registration be open, invitation-only, or off in the deployed demo?
- [ ] Where will the second-device and HTTPS checks be run, and how will you create the private certificate authority?

## 20. Definition of Done

- [ ] AC-01 to AC-112 and AC-114 to AC-118 pass or have a recorded measurement (AC-113 is optional).
- [ ] The ownership matrix, allergen property test, nutrient-maths tests, safety-rule tests and transaction tests pass in the normal suite.
- [ ] Migrations build the schema from an empty database, and a user can complete the demo journey with no manual database edits.
- [ ] The application runs in its containers on your computer, and you have opened it over HTTPS from a second device on your network.
- [ ] The README, diagrams, `DECISIONS.md`, `DATA_LICENCES.md` and test plan are complete, with known limitations and the safety thresholds' sources stated.
- [ ] You can explain every module, formula and safety rule without notes.

