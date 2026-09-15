# ADR-0001: Authentication, Authorization, and IDOR Protection Architecture

## Status
Accepted

## Context
ClarityKit is designed to analyze, extract evidence from, and prepare sensitive legal documents. Before any document ingestion or intelligence workflows can be implemented, the system must establish an uncompromising security foundation covering user identity, authentication, authorization, resource ownership, and multi-tenant data isolation.

## Decision

### 1. User Identity & Credential Management
- **Model**: Each user is represented by an immutable unique identifier (`user_id` as UUIDv4), unique lowercase `email`, `password_hash`, `name`, `is_active` status, and timestamps (`created_at`, `updated_at`).
- **Password Hashing**: We use standard cryptographic password hashing via `werkzeug.security` (`generate_password_hash` with `scrypt` / `pbkdf2:sha256`). Plaintext passwords and raw hashes are never exposed via API responses or logged.
- **Repository Interface**: In Phase 2, a clean `UserRepository` interface is used to decouple business logic from the underlying storage layer, ensuring seamless transition to PostgreSQL / SQLAlchemy in later phases.

### 2. Token-Based Authentication (JWT)
- **Token Format**: Standard JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).
- **Claims**: Tokens include standard claims: `sub` (user_id), `email`, `iat` (issued at), and `exp` (expiration timestamp).
- **Transport**: Bearer tokens via the `Authorization: Bearer <token>` header.
- **Validation**: Strict verification of signature, algorithm, and expiration. Malformed, expired, or tampered tokens return structured HTTP 401.
- **Identity Derivation**: Authenticated user identity is always derived from the verified token context, never from client request bodies or query parameters.

### 3. Server-Side Authorization & Strict IDOR Protection
- **Separation**: Authentication verifies identity; authorization verifies resource ownership and permissions.
- **IDOR Protection Policy**:
  - Unauthenticated request to protected resource → `HTTP 401 Unauthorized`
  - Authenticated request to nonexistent resource → `HTTP 404 Not Found`
  - Authenticated request to a resource owned by another user → `HTTP 404 Not Found` (returning 403 would leak resource existence)
  - Authenticated request to an owned resource → `HTTP 200 OK` (or allowed operation)
- **Ownership Enforcement**: Server-side `@require_ownership` decorator and authorization helpers enforce that all resource queries are scoped by `user_id`.

### 4. API Security & Error Sanitization
- **Generic Auth Failures**: Login failures return generic messages (`Invalid email or password`) to prevent account enumeration.
- **Structured JSON Errors**: All security exceptions return uniform JSON payloads (`{"error": "<code_string>", "message": "<sanitized_message>"}`) without leaking internal stack traces, tokens, or hashes.
- **CORS**: Retains restrictive explicit-origin configuration.

## Consequences
- **Positive**: Complete user isolation, airtight IDOR protection, robust security testing baseline, modular architecture ready for database integration.
- **Neutral**: Stateless JWTs require token expiry for session termination; blacklisting/refresh token mechanisms can be layered in subsequent phases if session revocation is needed.
