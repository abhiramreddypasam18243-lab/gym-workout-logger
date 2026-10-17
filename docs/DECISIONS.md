# Architecture & Design Decisions Log

Mirrors the Decisions Log in `spec.md` section 18 per **AC-116**. Every architectural trade-off, security choice, and placeholder safety threshold source is explicitly documented here.

## 1. Architectural & Engineering Decisions

| ID | Date | Decision | Alternatives Considered | Rationale |
| --- | --- | --- | --- | --- |
| **D-01** | 2026-10-16 | Modular monolith architecture | Microservices, serverless lambdas | Minimizes operational complexity and network latency; allows strict compile-time types, fast local integration tests, and clean domain isolation. |
| **D-02** | 2026-10-16 | React + TypeScript (Vite), FastAPI, PostgreSQL, SQLAlchemy 2 (Async) | Django, Next.js, Express, Go | End-to-end type safety with TypeScript and Pydantic; relational foreign key cascades, atomic transactions, and check constraints match training and diet data. |
| **D-03** | 2026-10-16 | Server-side revocable sessions in `HttpOnly`, `SameSite=Lax` cookies with CSRF tokens | Stateless JWTs, LocalStorage auth | Logout and account deletion can truly revoke credentials immediately on the server. `HttpOnly` cookies cannot be extracted by malicious clientside scripts (XSS). |
| **D-04** | 2026-10-16 | Argon2id password hashing | bcrypt, PBKDF2, scrypt | Memory-hard password hashing recommended by OWASP and modern cryptographic guidance, resistant to GPU/ASIC cracking. |
| **D-05** | 2026-10-16 | Transmit decimals as strings in API responses | Floating-point JSON numbers | Eliminates binary floating-point rounding errors (e.g., `0.1 + 0.2 = 0.30000000000000004`) in nutritional macro calculations and gym loads. |
| **D-06** | 2026-10-16 | Deterministic greedy meal planner with explicit scoring | Integer linear programming; blackbox ML | 100% reproducible, explainable, and testable; generates plans in milliseconds without external solver dependencies. |
| **D-07** | 2026-10-16 | Allergens are strict hard filters; unverified data is excluded | Treat unknown as safe | Catalogue data can be incomplete; a false inclusion of an allergen is dangerous, whereas a smaller plan is merely restrictive. |
| **D-08** | 2026-10-16 | Prep time & budget are hard caps only when set; cuisine/variety rank | Treat everything as ranking | Strict compliance with user-set limits while keeping meal variety and preferences flexible. |
| **D-09** | 2026-10-16 | Immutable nutrient snapshots on plan items and nutrition logs | Recompute dynamically from catalogue | Future catalogue edits or food deletions will never alter historical logs or audited meal plans. |
| **D-10** | 2026-10-16 | Foreign resources return HTTP 404 (Not Found) | HTTP 403 (Forbidden) | Prevents enumeration attacks; an attacker cannot probe IDs to determine whether a resource belongs to another user. |
| **D-11** | 2026-10-16 | No weight-loss or caloric deficit goals in v1 (`maintain` and `build_strength` only) | Aggressive deficit targets | Caloric deficit features carry eating-disorder risks beyond what this application can safely supervise without a doctor. |
| **D-12** | 2026-10-16 | Self-declared adult confirmation with optional birth date validation | Mandatory government ID verification | Minimizes collection of sensitive personal identity data while enforcing rule S2. |
| **D-13** | 2026-10-16 | Cursor-based pagination for workout history | Offset-based pagination | Immune to insertion skew (missing or duplicate rows) while scrolling through workout logs. |
| **D-14** | 2026-10-16 | Epley formula for estimated 1RM capped at 1–12 reps (`e1RM = load` at 1 rep) | Brzycki, Lombardi, O'Conner | Well-researched, universally understood in strength sports; capping at 12 reps avoids extrapolation error. |
| **D-15** | 2026-10-16 | Exact volume conversions (`1 cup = 240 ml`, `1 tbsp = 15 ml`, `1 tsp = 5 ml`) | Regional cup variances, guessed density | Completely predictable; avoids fabricating ingredient food densities. |
| **D-16** | 2026-10-16 | Mandatory TLS beyond localhost with private CA support | Plain HTTP across local network | Protects sessions and workout data from packet sniffing on local shared networks. |
| **D-17** | 2026-10-16 | Pure domain layering in `app/domain` | Mixed framework logic | Zero imports of FastAPI, SQLAlchemy, or system clock in domain algorithms; tested purely with unit and Hypothesis tests. |
| **D-18** | 2026-10-16 | Wellbeing controls: hide-calories, pause-nutrition, opt-in weight tracking | Mandatory calorie charting | Protects user wellbeing and avoids triggering obsessive dietary tracking behaviors (Rule S7). |
| **D-19** | 2026-10-16 | Curated seed catalogue with recorded sources and licenses | Massive web scraping | Prioritizes verified data accuracy and clear licensing over sheer volume. |
| **D-20** | 2026-10-16 | Automated architectural layering tests (`test_layering.py`) | Manual code reviews | Automatically prevents regressions in boundary layering during CI. |

---

## 2. Safety Thresholds & Citation Register (Rule S1–S10, AC-116)

All numeric safety thresholds in the application are consolidated in `app/config.py` and reviewed below:

1. **Mifflin–St Jeor BMR Equation:**
   - **Source:** Mifflin MD, St Jeor ST, et al. *"A new predictive equation for resting energy expenditure in healthy individuals."* Am J Clin Nutr. 1990; 51(2):241-247.
   - **Status:** Standard clinical equation for estimating Resting Metabolic Rate (RMR).

2. **Energy Floor Limits (Rule S5):**
   - **Values:** Minimum target estimate floor is **1,500 kcal/day**; hard plan generation minimum is **1,200 kcal/day**.
   - **Source:** Dietary Guidelines for Americans (USDA / HHS) and Academy of Nutrition and Dietetics.
   - **Status:** Placeholder safety boundary to prevent extreme calorie restriction. Explicitly marked as informational in UI disclaimer.

3. **Protein Intake Recommendation (Rule S6):**
   - **Values:** **1.6 g/kg/day** up to **2.2 g/kg/day**.
   - **Source:** Morton RW, et al. *"A systematic review, meta-analysis and meta-regression of the effect of protein supplementation on resistance training."* Br J Sports Med. 2018; 52(6):376-384.
   - **Status:** Evidence-based protein intake range for resistance-trained adults.

4. **Caloric Surplus for Strength Building:**
   - **Value:** **+5%** above estimated TDEE.
   - **Source:** Helms ER, et al. *"Evidence-based recommendations for natural bodybuilding contest preparation."* J Sports Med Phys Fitness. 2015.
   - **Status:** Conservative, non-aggressive caloric surplus for hypertrophy without excessive fat accrual.

5. **Epley 1RM Equation (Rule S4):**
   - **Formula:** $\text{e1RM} = \text{load} \times (1 + \frac{\text{reps}}{30})$ for reps $\in [1, 12]$.
   - **Source:** Epley B. *"Poundage Chart."* Boyd Epley Workout. Lincoln, NE: University of Nebraska; 1985.
   - **Status:** Standard resistance training performance formula.
