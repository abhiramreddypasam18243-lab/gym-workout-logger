# Decisions Log

All decisions from the spec (section 18) plus project-specific choices made during build.

| ID | Date | Decision | Alternatives | Why |
| --- | --- | --- | --- | --- |
| D-01 | 2026-10-16 | A modular monolith | Microservices | Less operational complexity, same clean boundaries, easier to test and explain |
| D-02 | 2026-10-16 | React and TypeScript, FastAPI, PostgreSQL, SQLAlchemy 2 and Alembic, as the blueprint recommends | Other stacks | Typed end to end, relational constraints and transactions suit this data |
| D-03 | 2026-10-16 | Server-side revocable sessions in an `HttpOnly` cookie, with a CSRF token | Stateless JWTs | Logout and account deletion can truly revoke access, and cookies are not readable by scripts |
| D-04 | 2026-10-16 | Argon2id password hashing | bcrypt | Memory-hard, and current guidance favours it |
| D-05 | 2026-10-16 | Decimals travel as strings in the API | JSON numbers | No floating-point surprises in nutrient and load values |
| D-06 | 2026-10-16 | A deterministic greedy planner with an explicit scoring formula | Integer programming; ML | Reproducible, explainable and testable |
| D-07 | 2026-10-16 | Allergens are hard filters, unverified allergen data excluded by default | Treat unknown as safe | Catalogue data can be incomplete; wrong inclusion is worse than a smaller plan |
| D-08 | 2026-10-16 | Time and budget are hard caps only when user sets them; cuisine and variety only rank | Treat everything as ranking | Matches the blueprint's "filters" while keeping preferences flexible |
| D-09 | 2026-10-16 | Nutrient snapshots on plan and log items, catalogue version in each plan | Recompute from live catalogue | Later corrections never silently rewrite history |
| D-10 | 2026-10-16 | A foreign resource returns 404, same as a missing one | 403 | Does not reveal that the record exists |
| D-11 | 2026-10-16 | No weight-loss or deficit goals in v1; only `maintain` and `build_strength` | Include a cut goal | Strength-focused; deficit features carry more risk than this project can manage |
| D-12 | 2026-10-16 | Self-declared adult confirmation, plus birth-date check when given | Collect birth date from everyone | Collects less sensitive data; limitation documented |
| D-13 | 2026-10-16 | Cursor pagination | Offset pagination | Stable under inserts, no duplicates or gaps |
| D-14 | 2026-10-16 | Epley e1RM for 1 to 12 reps, with `e1RM = load` at 1 rep | Brzycki; any rep count | Simple, well known, rep range limits the error |
| D-15 | 2026-10-16 | `1 cup = 240 ml`, `1 tbsp = 15 ml`, `1 tsp = 5 ml`, no mass-volume conversion | Regional cup sizes; density tables | Predictable, avoids inventing densities |
| D-16 | 2026-10-16 | Credentials only over TLS beyond localhost, with mkcert private CA | Plain HTTP on the network | Passwords and sessions must not be readable on the network |
| D-17 | 2026-10-16 | Frontend API types generated from the OpenAPI document | Hand-written types | Front and back end cannot drift apart without CI failing |
| D-18 | 2026-10-16 | Neutral wording, hide-calories, pause, opt-in weight tracking | Always show everything | Reduces harm for users for whom numbers are unhelpful |
| D-19 | 2026-10-16 | A small reviewed catalogue with recorded sources and licences | Import a very large database | Quality, licence clarity and testability before scale |
| D-20 | 2026-10-16 | An automated layering check (domain imports nothing from frameworks) | Convention only | Keeps the rules pure and testable |
| D-21 | 2026-10-17 | Food data: USDA FoodData Central + Indian Food Composition Tables (IFCT/NIN) | USDA only | Broader coverage including Indian foods; both are government publications |
| D-22 | 2026-10-17 | Seed recipes cover 5 cuisines: Indian, Italian, Mexican, American, East Asian | 4 cuisines | More variety; spec requires at least 4 |
| D-23 | 2026-10-17 | Include optional Mifflin–St Jeor calorie estimate with full transparency | Manual targets only | Users benefit from a starting point; all inputs/assumptions shown |
| D-24 | 2026-10-17 | Default currency INR, default units kg; users can switch to lb | USD/lb | Project context is India-based |
| D-25 | 2026-10-17 | Open registration, toggleable via `REGISTRATION_ENABLED` env var | Invitation-only | Simplest for development; can be disabled for demo |
| D-26 | 2026-10-17 | TLS via mkcert private CA | Caddy auto-certs; manual OpenSSL | One command, well-documented, works on all platforms |
| D-27 | 2026-10-19 | New accounts start with "beef" in excluded ingredients (`DEFAULT_EXCLUDED_INGREDIENTS`); users can remove it | Remove beef from the catalogue; swap beef for chicken or mutton | India-focused app where many users avoid beef; keeps the catalogue intact and the choice with the user |
