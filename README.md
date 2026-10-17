# Titan — Elite Gym Workout Logger & Strength-Focused Diet Planner

[![CI Pipeline](https://github.com/abhiramreddypasam18243-lab/gym-workout-logger/actions/workflows/ci.yml/badge.svg)](https://github.com/abhiramreddypasam18243-lab/gym-workout-logger/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-109%20passed-10b981?style=flat-square)
![Security](https://img.shields.io/badge/pip--audit-0%20vulnerabilities-10b981?style=flat-square)
![Frontend](https://img.shields.io/badge/frontend-React%2019%20%7C%20Vite%20%7C%20TypeScript-38bdf8?style=flat-square)
![Backend](https://img.shields.io/badge/backend-FastAPI%20%7C%20SQLAlchemy%202%20%7C%20PostgreSQL%2016-38bdf8?style=flat-square)
![Design](https://img.shields.io/badge/design-Level%20100%20Titanium%20SaaS-f59e0b?style=flat-square)

A production-grade, full-stack athletic performance cockpit combining workout logging, automated progressive overload telemetry, e1RM analytics, and a deterministic, rule-based dietary planning engine.

> **Disclaimer:** This application provides informational estimates only. It is not medical advice and is not a substitute for guidance from a registered dietitian or doctor.

---

## ⚡ Level 100 Athletic SaaS User Interface

The interface features a state-of-the-art dark titanium design system inspired by Whoop, Apple Fitness+, and Linear:

- **Atmospheric Dark Titanium Design System**: Dual breathing radial auras (`#38bdf8` cyan and `#10b981` emerald) with dynamic CSS pulse animations, microdot telemetry texture backdrop, and glassmorphism 2.0 cards with specular top rim highlights (`inset 0 1px 0 rgba(255,255,255,0.15)`).
- **Interactive Recovery Rest Timer HUD**: Floating interactive widget with a circular SVG countdown ring, quick presets (**30s, 60s, 90s, 2m, 3m**), `-15s` / `+15s` micro-adjusters, and automatic triggers on set completion.
- **Zero-Latency Web Audio API Synthesis**: Pure browser-native sound generation without external asset requests. Synthesizes harmonic dual-tone set completion chimes, rest expiration fanfare, and tactile feedback with persistent mute/unmute control.
- **Global Command Palette (`Ctrl+K` / `⌘K`)**: Instant fuzzy-search spotlight navigation with arrow key navigation across exercises, routines, food logs, and app controls.
- **Live Session Telemetry Cockpit**: Real-time workout duration timer, live working volume calculator (`Load × Reps`), working sets completed counter, real-time Epley e1RM calculation badge, and green glowing row animations upon completing sets.
- **Strength Analytics Spline Trajectory**: Dynamic cubic bezier SVG area spline curve with vertical grid ticks, glowing data nodes, gold milestone star markers for peak personal records, and hover telemetry tooltips.
- **Dashboard Telemetry Strip**: Dynamic time-of-day athlete greetings, animated streak badge (`🔥 7-DAY STREAK`), circular SVG progress ring gauge, and monospace telemetry stat cards.

---

## 🛠 Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16 / SQLite (aiosqlite)
- **Frontend:** React 19, TypeScript, Vite, Web Audio API, Vanilla CSS Design System
- **Security & Quality:** Argon2id password hashing, HttpOnly session cookies, SameSite=Lax, CSRF token validation, non-root Docker container (`appuser`), 100% automated test coverage (109 pytest cases), zero pip-audit vulnerabilities.
- **Infrastructure:** Docker Compose, Render single-container full-stack deployment, GitHub Actions CI.

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Node.js 22+](https://nodejs.org/) (for frontend development)
- [Python 3.12+](https://www.python.org/) (for backend development)

### Running with Docker Compose

```bash
# 1. Clone the repository
git clone https://github.com/abhiramreddypasam18243-lab/gym-workout-logger.git
cd gym-workout-logger

# 2. Copy environment file and set secrets
cp .env.example .env
# Edit .env — change POSTGRES_PASSWORD, SECRET_KEY, etc.

# 3. Build and launch containers
docker compose up -d --build

# 4. Open the application in your browser
# http://localhost:8080
```

### Seed Data & Synthetic Demo Account

```bash
# Seed reviewed food and exercise catalogue
docker compose run --rm backend python -m app.seed

# Generate synthetic demo account (2 years of progressive overload data, ~10,000 sets)
docker compose run --rm backend python -m app.demo_user
```

### Local Development Setup

```bash
# Backend Setup
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # Windows (or source .venv/bin/activate on Linux/macOS)
pip install -e ".[dev]"
pytest -q                         # Run full 109 test suite
uvicorn app.main:app --reload --port 8000

# Frontend Setup (in separate terminal)
cd frontend
npm install
npm run dev                       # Vite hot-reload server at http://localhost:5173
npm run build                     # Production compilation
```

---

## 🧪 Safety Thresholds & Scientific Citations (AC-116)

All numeric thresholds are consolidated in `backend/app/config.py` and cite peer-reviewed clinical and exercise science literature:

| Parameter | Value | Scientific Citation / Source |
|---|---|---|
| `estimate_floor_kcal` | 1,500 kcal | Dietary Guidelines for Americans (USDA/HHS); placeholder floor preventing extreme deficits |
| `plan_minimum_kcal` | 1,200 kcal | Clinical minimum safe energy threshold for sedentary adults without medical supervision |
| **BMR Formula** | Mifflin–St Jeor | Mifflin MD, St Jeor ST, et al. *Am J Clin Nutr.* 1990; 51(2):241–247 |
| **Activity Multipliers** | 1.2 to 1.725 | FAO/WHO/UNU Scientific Consultation on Human Energy Requirements (2004) |
| **Protein Target** | 1.6 to 2.2 g/kg | Morton RW, et al. *Br J Sports Med.* 2018; 52(6):376–384 (resistance training meta-analysis) |
| **Strength Surplus** | +5% TDEE | Helms ER, et al. *J Sports Med Phys Fitness.* 2015 (lean mass accrual without fat gain) |
| **e1RM Formula** | Epley | Epley B. *Boyd Epley Workout.* Lincoln, NE: Univ. of Nebraska; 1985 (valid for 1–12 reps) |

---

## 📖 Known Limitations (v1, AC-118)

Per specification AC-118, the initial release intentionally operates with the following explicit scope boundaries:
1. **Self-Declared Adult Confirmation:** Age verification relies on self-confirmation (Rule S2) rather than external KYC or identity document scanning.
2. **Authentication Scope:** No third-party OAuth, SMS, or email recovery in v1; accounts use server-side argon2id credentials and revocable HttpOnly cookies.
3. **Nutrient Approximation:** Reference values are sourced from USDA FoodData Central and IFCT; naturally occurring agricultural variations mean all micro and macro numbers are approximate.
4. **Volume-Mass Density Independence:** The grocery checklist aggregates identical units (`g` + `g`, `ml` + `ml`) but does not perform synthetic mass-to-volume conversions (e.g. converting `tbsp` of olive oil to `grams` without empirical food density tables).
5. **Greedy Planner Heuristic:** The meal plan generator uses a deterministic, explainable greedy scoring algorithm rather than an integer linear programming (ILP) solver; it finds feasible, high-variety plans quickly but does not claim mathematical global optimality.

---

## 📚 Documentation Index

- [`docs/DECISIONS.md`](docs/DECISIONS.md) — Complete 20-decision engineering architecture log (D-01 to D-20)
- [`docs/DATA_LICENCES.md`](docs/DATA_LICENCES.md) — Data sources, public domain notices, and license tracking
- [`docs/test-plan.md`](docs/test-plan.md) — Acceptance criteria (AC-01 to AC-118) verification matrix
- [`docs/learning-log.md`](docs/learning-log.md) — Comprehensive viva learning log with design rationale & quiz questions
- [`spec.md`](spec.md) — Master specification document

---

## 📄 Licence

Academic Project — Developed for undergraduate viva presentation and evaluation.
