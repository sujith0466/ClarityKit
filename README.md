# ClarityKit

> An evidence-grounded legal document understanding and preparation platform that transforms complex legal documents into understandable, traceable, and actionable information without pretending to be a lawyer.

## Core Philosophy

**UNDERSTAND → EXTRACT → EVIDENCE → ASSIST → PREPARE**

---

## Current Status: Phase 1 — Project Foundation

Phase 1 establishes the verified engineering foundation:
- Clean Flask backend with application factory, configuration boundaries, standard JSON error handling, and health smoke tests.
- React + TypeScript + Vite frontend with modular shell architecture, error boundaries, accessible semantic layout, and Vitest component smoke tests.
- Unified quality tooling (Ruff, Mypy, ESLint, Prettier, TypeScript).
- GitHub Actions CI workflow covering all backend and frontend validation steps.

> [!NOTE]
> Phase 1 is engineering foundation only. Intelligence layers (Evidence Engine, Trust Engine, Reasoning), document ingestion, OCR, vector search, database models, and legal workflows will be introduced in subsequent phases according to the Master Plan.

---

## Repository Structure

```text
claritykit/
├── .github/
│   └── workflows/
│       └── ci.yml             # Unified GitHub Actions CI
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── health.py      # Health smoke endpoint (/api/health)
│   │   ├── __init__.py        # Flask application factory
│   │   ├── config.py          # Environment configuration & CORS
│   │   └── errors.py          # Standard JSON error handlers
│   ├── tests/
│   │   ├── conftest.py        # Pytest fixtures
│   │   ├── test_config.py     # Configuration tests
│   │   ├── test_errors.py     # Error handling tests
│   │   ├── test_factory.py    # App factory tests
│   │   └── test_health.py     # Health smoke test
│   ├── pyproject.toml         # Ruff, Mypy, and Pytest configuration
│   └── requirements.txt       # Pinned Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ErrorBoundary/ # Resilient React ErrorBoundary
│   │   │   └── Shell/         # Accessible Header, Footer, MainLayout
│   │   ├── types/             # TypeScript definitions
│   │   ├── App.tsx            # Application shell
│   │   ├── App.test.tsx       # Shell smoke tests
│   │   ├── config.ts          # Safe frontend configuration
│   │   ├── config.test.ts     # Config tests
│   │   ├── setupTests.ts      # Test setup & matchers
│   │   ├── main.tsx           # React entry point
│   │   ├── App.css
│   │   └── index.css
│   ├── eslint.config.js       # ESLint configuration
│   ├── index.html
│   ├── package.json           # Pinned npm dependencies & scripts
│   ├── tsconfig.json          # TypeScript compiler configuration
│   └── vite.config.ts         # Vite bundler & Vitest test runner
├── docs/
│   ├── decisions/             # Architecture Decision Records (ADRs)
│   └── progress-tracker.md    # Master Progress Tracker
├── scripts/
│   ├── check.sh               # Unix full-suite quality & test runner
│   └── check.ps1              # Windows full-suite quality & test runner
├── .env.example               # Safe environment configuration template
├── .gitignore                 # Exclusion rules
└── README.md                  # Project overview & documentation
```

---

## Getting Started

### Prerequisites

- **Python**: >= 3.11 (tested on 3.12 / 3.13)
- **Node.js**: >= 20.x
- **npm**: >= 10.x

---

### Quick Start (Full Quality & Test Verification)

Run the unified project quality suite:

- **Linux / macOS**:
  ```bash
  bash scripts/check.sh
  ```

- **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/check.ps1
  ```

---

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   source .venv/bin/activate
   ```

3. Install pinned dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run tests:
   ```bash
   pytest
   ```

5. Run linting and type checking:
   ```bash
   ruff check .
   ruff format --check .
   mypy app
   ```

6. Start the development server:
   ```bash
   python -m flask --app "app:create_app()" run --port 5000
   ```
   The health check will be available at `http://127.0.0.1:5000/api/health`.

---

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install pinned dependencies:
   ```bash
   npm install
   ```

3. Run smoke and unit tests:
   ```bash
   npm run test
   ```

4. Run code quality checks:
   ```bash
   npm run lint
   npm run format:check
   npm run typecheck
   ```

5. Start the frontend development server:
   ```bash
   npm run dev
   ```
   The application will be served at `http://localhost:5173`.

---

## Continuous Integration (CI)

Every push and pull request against `main` or `master` triggers the GitHub Actions workflow (`.github/workflows/ci.yml`), executing:
- **Backend**: Python 3.12, dependency installation, `ruff check`, `ruff format --check`, `mypy app`, `pytest`.
- **Frontend**: Node 20, `npm ci`, `prettier --check`, `eslint`, `tsc --noEmit`, `vitest run`, `vite build`.

---

## Architectural Constraints

- **Single Reasoning Gateway**: In later phases, `reasoning/` will be the ONLY application module directly invoking generative LLM APIs.
- **Evidence-Grounded**: All extractions and analyses require precise document citation and traceability.
