# ClarityKit

> An evidence-grounded legal document understanding and preparation platform that transforms complex legal documents into understandable, traceable, and actionable information without pretending to be a lawyer.

## Core Philosophy

**UNDERSTAND → EXTRACT → EVIDENCE → ASSIST → PREPARE**

---

## Current Status: Phase 2 — Authentication & Security Foundation

Phase 2 establishes the identity, authentication, authorization, and tenant isolation boundaries:
- **User Identity & Password Security**: Cryptographic password hashing (`scrypt` / `pbkdf2:sha256`), sanitized user entities, no password leakage in logs or responses.
- **Stateless Authentication (JWT)**: HMAC-SHA256 signed tokens (`HS256`), strict expiration and signature verification, protected endpoints via `@require_auth`.
- **Server-Side Authorization & IDOR Protection**: `@require_ownership` decorator enforcing that non-owned resources return `HTTP 404 Not Found` (never 403) to prevent resource existence enumeration.
- **Frontend Security Shell**: Accessible login and registration forms, `AuthContext` state management, and protected component boundaries.
- **Unified Quality & Security Test Suite**: 36 backend tests and 13 frontend tests covering positive authentication, attack simulations (IDOR, forged JWTs, ID substitutions), accessibility, and regression checks.

> [!NOTE]
> Phase 2 is security infrastructure only. Legal document ingestion, PDF parsing, OCR, vector embeddings, pgvector, and LLM reasoning will be incrementally introduced in subsequent phases according to the Master Plan.

---

## Security Architecture & API Endpoints

### Authentication Endpoints
- `POST /api/auth/register` — Register new user account (`email`, `password`, `name`).
- `POST /api/auth/login` — Authenticate user and receive JWT token (`email`, `password`).
- `POST /api/auth/logout` — Acknowledge session termination.
- `GET /api/auth/me` — Retrieve authenticated user profile (requires `Authorization: Bearer <token>`).

### Authorization & IDOR Policy
- **Unauthenticated access to protected resource** → `HTTP 401 Unauthorized`
- **Authenticated access to nonexistent resource** → `HTTP 404 Not Found`
- **Authenticated access to another user's resource** → `HTTP 404 Not Found` (strict IDOR protection)
- **Authenticated access to owned resource** → `HTTP 200 OK`

---

## Repository Structure

```text
claritykit/
├── .github/
│   └── workflows/
│       └── ci.yml             # Unified GitHub Actions CI
├── backend/
│   ├── app/
│   │   ├── auth/              # Authentication & Security core
│   │   │   ├── context.py     # @require_auth & @require_ownership
│   │   │   ├── models.py      # User entity
│   │   │   ├── password.py    # Cryptographic password hashing
│   │   │   ├── repository.py  # Pluggable user repository interface
│   │   │   ├── service.py     # AuthService business logic
│   │   │   └── tokens.py      # JWT token generator & validator
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # /api/auth routes
│   │   │   └── health.py      # Health smoke endpoint (/api/health)
│   │   ├── __init__.py        # Flask application factory
│   │   ├── config.py          # Security & environment configuration
│   │   └── errors.py          # Standard JSON error handlers
│   ├── tests/
│   │   ├── conftest.py        # Pytest fixtures
│   │   ├── test_auth.py       # Authentication unit & API tests
│   │   ├── test_authorization.py # Authorization, ownership & IDOR tests
│   │   ├── test_config.py     # Configuration tests
│   │   ├── test_errors.py     # Error handling tests
│   │   ├── test_factory.py    # App factory tests
│   │   ├── test_health.py     # Health smoke test
│   │   └── test_security_regressions.py # Security regression tests
│   ├── pyproject.toml         # Ruff, Mypy, and Pytest configuration
│   └── requirements.txt       # Pinned Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Auth/          # LoginForm & RegisterForm
│   │   │   ├── ErrorBoundary/ # Resilient React ErrorBoundary
│   │   │   └── Shell/         # Accessible Header, Footer, MainLayout
│   │   ├── context/           # AuthContext & useAuth hook
│   │   ├── types/             # TypeScript definitions
│   │   ├── App.tsx            # Main application shell
│   │   ├── App.test.tsx       # Shell tests
│   │   ├── config.ts          # Safe frontend configuration
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
│   ├── check.sh               # Unix full-suite quality & security runner
│   └── check.ps1              # Windows full-suite quality & security runner
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

### Quick Start (Full Quality & Security Verification)

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

1. Navigate to `backend/` and set up virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run security and unit tests:
   ```bash
   pytest
   ```

3. Run linting and type checking:
   ```bash
   ruff check .
   ruff format --check .
   mypy app
   ```

4. Start backend server:
   ```bash
   python -m flask --app "app:create_app()" run --port 5000
   ```

---

### Frontend Setup

1. Navigate to `frontend/` and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run tests:
   ```bash
   npm run test
   ```

3. Run code quality checks:
   ```bash
   npm run lint
   npm run format:check
   npm run typecheck
   ```

4. Start frontend server:
   ```bash
   npm run dev
   ```

---

## Continuous Integration (CI)

GitHub Actions workflow (`.github/workflows/ci.yml`) executes on every commit and PR:
- **Backend**: Python 3.12, dependency installation, `ruff check`, `ruff format --check`, `mypy app`, and complete `pytest` security suite.
- **Frontend**: Node 20, `npm ci`, `prettier --check`, `eslint`, `tsc --noEmit`, `vitest run`, and `vite build`.

---

## Architectural Constraints

- **Single Reasoning Gateway**: In later phases, `reasoning/` will be the ONLY application module directly invoking generative LLM APIs.
- **Evidence-Grounded**: All document analyses require verifiable citations and traceability.
- **Tenant Isolation**: All resource operations are authenticated and strictly scoped to the authenticated user ID.
