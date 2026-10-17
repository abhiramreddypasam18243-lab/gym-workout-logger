# System Architecture Diagram

Comprehensive architectural diagram detailing layer boundaries, security middleware, pure domain modules, and deployment topology (AC-115).

## 1. Application Layer Hierarchy & Boundaries (Rule AC-98, D-01, D-17)

```mermaid
graph TD
    subgraph ClientBrowser ["Client Tier (Browser / Mobile 360px)"]
        UI["React 19 + TypeScript (Vite)"]
        Ctx["AuthContext & Unit Converter State"]
        APIClient["API Client (CSRF + HttpOnly Session)"]
        UI --> Ctx
        Ctx --> APIClient
    end

    subgraph ReverseProxyTier ["Infrastructure & Reverse Proxy"]
        NginxProxy["Nginx / TLS 1.2+ Proxy (Port 8443 / 8080)"]
        NginxProxy -->|"Forwarded-Proto TLS"| BackendAPI
    end

    APIClient -->|"HTTPS / Cookie Credentials"| NginxProxy

    subgraph BackendApp ["FastAPI Modular Monolith (Python 3.12, appuser)"]
        subgraph MiddlewareStack ["Security & Limits Middleware"]
            BodyLimit["1MB Body Size Limiter (SEC8, AC-13)"]
            SecHeaders["Security Headers (CSP, HSTS, X-Frame-Options)"]
            CSRFCheck["Double Submit CSRF Middleware"]
            BodyLimit --> SecHeaders
            SecHeaders --> CSRFCheck
        end

        subgraph RoutersLayer ["Thin Routers (app/api)"]
            AuthRouter["Auth Router (/api/auth)"]
            WorkoutRouter["Workout Router (/api/workouts, /api/routines)"]
            StrengthRouter["Strength Router (/api/analytics)"]
            PlannerRouter["Meal Planner Router (/api/meal-plans)"]
            LogRouter["Nutrition Log Router (/api/nutrition/logs)"]
            DashboardRouter["Dashboard Router (/api/dashboard)"]
            DataControlsRouter["Data Controls (/api/export, /api/account)"]
        end

        subgraph ServicesLayer ["Business Services (app/services)"]
            AuthSvc["AuthService (Argon2id, Session Manager)"]
            WorkoutSvc["WorkoutService (Atomic Session Writes)"]
            StrengthSvc["StrengthAnalyticsService (Volume & e1RM Trends)"]
            PlannerSvc["MealPlanService (Greedy Planner, Scoring)"]
            NutritionLogSvc["NutritionLogService (Snapshots, Tolerances)"]
            DashboardSvc["DashboardService (Aggregations, Insights)"]
            DataControlsSvc["DataControlsService (Schema Validation, Deletion)"]
        end

        subgraph DomainLayer ["Pure Domain Logic (app/domain) - ZERO Framework Imports"]
            UnitsDomain["domain.units (Metric & Imperial Maths)"]
            StrengthDomain["domain.strength (Epley 1RM, PR Detection, Volume)"]
            TargetsDomain["domain.targets (Mifflin-St Jeor, Activity, Macros)"]
            NutrientsDomain["domain.nutrients (Atwater Checks, Scaling)"]
            ScoringDomain["domain.scoring (Deterministic Meal Scoring)"]
            GroceryDomain["domain.grocery (Unit-Preserving Aggregation)"]
            ComparisonDomain["domain.comparison (Planned vs Logged Deltas)"]
            InsightsDomain["domain.insights (Non-Causal Observations, Banned Words)"]
        end

        subgraph DataAccessLayer ["Data Access & Models (SQLAlchemy 2 Async)"]
            DBModels["SQLAlchemy Declarative Models (24 Tables)"]
            AsyncEngine["Async Engine (asyncpg pool, pool_pre_ping)"]
            AlembicMig["Alembic Migrations Versioning"]
        end
    end

    BackendAPI --> MiddlewareStack
    MiddlewareStack --> RoutersLayer

    AuthRouter --> AuthSvc
    WorkoutRouter --> WorkoutSvc
    StrengthRouter --> StrengthSvc
    PlannerRouter --> PlannerSvc
    LogRouter --> NutritionLogSvc
    DashboardRouter --> DashboardSvc
    DataControlsRouter --> DataControlsSvc

    WorkoutSvc --> StrengthDomain
    StrengthSvc --> StrengthDomain
    PlannerSvc --> TargetsDomain
    PlannerSvc --> ScoringDomain
    PlannerSvc --> NutrientsDomain
    PlannerSvc --> GroceryDomain
    NutritionLogSvc --> NutrientsDomain
    DashboardSvc --> ComparisonDomain
    DashboardSvc --> InsightsDomain

    AuthSvc --> DBModels
    WorkoutSvc --> DBModels
    StrengthSvc --> DBModels
    PlannerSvc --> DBModels
    NutritionLogSvc --> DBModels
    DashboardSvc --> DBModels
    DataControlsSvc --> DBModels

    DBModels --> AsyncEngine

    subgraph StorageTier ["Database Tier"]
        PostgresDB[(PostgreSQL 16 Engine - pgdata volume)]
    end

    AsyncEngine -->|"Connection Pool TCP"| PostgresDB
    AlembicMig -->|"Schema Evolution"| PostgresDB
```

---

## 2. Architectural Principles & Constraints

1. **Strict Layering (AC-98):**
   - The `app/domain` package is mathematically pure: it contains zero imports of `fastapi`, `sqlalchemy`, `pydantic`, `datetime.utcnow`, or any network/database library. Tested by `tests/test_layering.py`.
2. **Atomic Multi-Row Writes (NFR Reliability):**
   - Workouts, routines, meal plan substitutions, and nutrition intake logs commit in atomic transactions. A failure on a set or ingredient rolls back the entire session.
3. **Defense in Depth Security (SEC1–SEC12):**
   - Argon2id password hashing with unique salt.
   - HttpOnly, SameSite=Lax session cookies preventing token theft via XSS.
   - Double-submit CSRF protection on all mutating endpoints (`POST`, `PATCH`, `DELETE`).
   - Rate limiting on failed authentication attempts.
   - 1 MB request body hard limit.
4. **Data Sovereignty (AC-88, AC-89):**
   - Full JSON export validated against `export_schema.json`.
   - Permanent account deletion wiping all 16 user-owned tables while preserving shared catalogue data.
