

The spec above is the source of truth. If the code and the spec disagree, stop and tell me which one should change. Do not quietly change either. The original assignment blueprint is `docs/Advanced_Gym_Workout_Logger_Diet_Planning_Blueprint.docx`; the spec's section 14 maps its requirements onto the spec's.

## About me and this project

I am an undergraduate student building this as a graded project. I will be quizzed on it in a viva, so I must understand every module. I want to finish as fast as possible, so keep the pace high and the explanations short.

## How to work

1. **Follow the build order in section 17 of the spec**, one step at a time. Finish a step (all its acceptance criteria passing) before starting the next. Do not stop in the middle of a step unless you are blocked, a **[LEARN]** module comes up, or the spec has an open question you need me to answer.
2. **Tests first.** For each acceptance criterion, write the failing test, then the code that makes it pass. Name each test after its AC ID (for example `test_ac_41_pr_detection`).
3. **Derive expected values by calculation**, as the acceptance criteria do. Never copy the application's own output into a test as the expected answer, and never edit a test value or a threshold to make a test pass. If a test seems wrong, tell me.
4. **Run the full checks after every change:** formatting, lint, type checks, migrations and tests. Show me the results at the end of each step.
5. **Move fast.** Do not pause for review between modules. At the end of each step, give me a short summary: files changed, tests passing, anything I should check.
6. **Ask before deciding.** If the spec leaves a choice open (section 19), ask me. When we decide, add a row to the Decisions Log in `SPEC.md` and to `DECISIONS.md`.
7. **Do not add features** that are not in the spec. Suggest them at the end instead.

## Learning rules

- At the end of each step, add a short entry to `docs/learning-log.md`: what was built, why it is designed that way, one thing that could go wrong, and 3 quiz questions for me (no answers; I will answer them myself).
- These modules are marked **[LEARN]**. For them, first explain the design and the key edge cases in a few sentences, then let me write the first version myself and review it afterwards:
  - The plan generator's filters, scoring and selection (spec section 5.5, AC-56 to AC-65)
  - Nutrient scaling, recipe totals and grocery unit aggregation (spec sections 5.3 and 5.7, AC-45 to AC-47, AC-77 to AC-79)
  - Sessions, CSRF protection and the ownership checks (spec section 10, AC-03 to AC-08)
  - e1RM, volume and PR detection (spec section 5.2, AC-39 to AC-41)
- If I say "you write it" for a **[LEARN]** module, write it, and still add its learning-log entry.
- If I ask "why", explain with a small concrete example, not just a definition.

## Safety rules (never relax these)

- **Never invent nutrient data.** Seed foods and recipes must come from a source I name, with its licence recorded in `docs/DATA_LICENCES.md`. If I have not supplied a dataset, ask me for one. Values made up for tests go only in clearly marked fixtures (spec AC-47), never in the seed catalogue.
- **Allergies are hard filters.** Never weaken, bypass or reorder them to make a plan feasible, and never suggest removing an allergy to fix an `infeasible` result.
- **Implement spec section 3 exactly** (adults only, professional-guidance flag, energy floors, no deficit or weight-loss goals, hide-calories, pause, opt-in weight tracking, neutral language, disclaimers). Do not add features that encourage restriction, shaming, streak pressure or body-weight targets.
- **No medical claims.** Never write text that presents an estimate as medical advice or promises an outcome.
- The numeric safety thresholds are placeholders for me to review. Keep them in one configuration module, and do not present them as authoritative.

## Project rules

- **Layering:** `app/domain` contains pure functions with no framework, database or clock imports. Routers are thin; rules live in services and domain functions; every query is scoped to the authenticated user.
- **Identity:** always derive the user from the session. Request schemas forbid unknown fields.
- **Exact numbers:** use `Decimal` and `NUMERIC`, transmit decimals as strings, and round only for display.
- **Time:** store UTC, and compute days and weeks in the user's IANA timezone. Inject the clock so tests control time.
- **Transactions:** every multi-row write (workouts, plans, logs) is atomic.
- **Secrets:** only in environment variables. Never commit `.env`. Never log passwords, tokens, session IDs or full emails.
- **Dependencies and versions:** pin them, and ask before adding a new dependency.
- **Tests use PostgreSQL**, never SQLite, because constraints and plans must match production.
- **Deployment:** the project must always run with Docker Compose (spec section 11). Build the walking-skeleton Compose stack in step 1, keep it working, and rebuild after each step. Application containers run as non-root, and credentials from non-localhost clients are accepted only over TLS.

## Commands

I have not verified the exact commands for the versions you choose. Correct this list as the real commands appear.

- Backend tests: `cd backend && pytest -q`
- Lint and types: `cd backend && ruff check . && mypy .`; `cd frontend && npm run lint && npx tsc --noEmit`
- Migrations: `cd backend && alembic upgrade head` (and `alembic check`)
- Frontend tests: `cd frontend && npm test`
- End-to-end tests: `cd frontend && npx playwright test`
- Seed the catalogue: `docker compose run --rm backend python -m app.seed`
- Create the synthetic demo account: `docker compose run --rm backend python -m app.demo_user`
- Run the deployed service: `docker compose up -d --build`, then open `http://localhost:8080`

## Git

Commit after each completed step, with a message that names the AC IDs, for example `Add sessions, CSRF and ownership tests (AC-01 to AC-13)`.