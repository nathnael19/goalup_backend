# GoalUp Backend — Security Vulnerability Audit

**Audit date:** March 2025  
**Scope:** `goalup_backend` application code (auth, API endpoints, config, file uploads, dependencies).

---

## Executive Summary

| Severity | Count | Status |
|----------|--------|--------|
| **Critical** | 1 | ✅ Fixed |
| **High**     | 3 | ✅ Partially fixed (see below) |
| **Medium**  | 6 | ✅ Some fixed; rest documented |
| **Low**     | 4 | Documented |

**Immediate fixes applied:** Sensitive user data no longer returned in login/refresh/user create; internal error details no longer leaked to clients; refresh endpoint rate-limited; PyJWT upgraded. Remaining items are documented for your prioritization.

---

## 1. Authentication & Authorization

### 1.1 ✅ FIXED — Sensitive user fields in login/refresh/user responses (Critical)

- **Location:** `app/api/v1/endpoints/auth.py` (login, refresh), `app/api/v1/endpoints/users.py` (create, read, update).
- **Issue:** Responses used `user.model_dump()` / `db_user.model_dump()`, exposing the full `User` model: `hashed_password`, `failed_login_attempts`, `lockout_until`, `is_deleted`, etc.
- **Fix:** All relevant responses now use `UserRead.model_validate(user).model_dump()` (plus `profile_image_url` where used), so only safe fields are returned.

### 1.2 ✅ FIXED — Refresh token endpoint not rate-limited (Medium)

- **Location:** `app/api/v1/endpoints/auth.py` — `POST /refresh`.
- **Issue:** No rate limit allowed refresh-token brute force or abuse.
- **Fix:** `@limiter.limit("10/minute")` added to the refresh endpoint.

### 1.3 Verified — JWT and role checks

- JWT decode uses fixed `algorithms=[settings.ALGORITHM]` (no algorithm confusion).
- Role checks in `deps.py` and tournament-scoping for Tournament Admins are in place.
- `PATCH /me` does not allow changing `role`, `is_active`, or `is_superuser`; admin user update restricts Tournament Admins appropriately.

---

## 2. Input Validation & Injection

- **SQL injection:** None found. Data access uses SQLModel/SQLAlchemy ORM with parameterized queries.
- **Command/code injection:** No `eval`, `exec`, or `subprocess` in app code.
- **Recommendation:** Continue using the ORM; avoid raw SQL or string concatenation with user input.

---

## 3. Sensitive Data

- **Secrets:** `SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `RESEND_API_KEY` etc. are loaded from environment/`.env` via pydantic-settings; no hardcoded secrets in code.
- **Scripts:** `create_admin.py` uses `ADMIN_PASSWORD` from env; ensure `.env` is in `.gitignore` and never committed.
- **PII in logs (Medium):** In `auth.py`, password reset failure logs the email. Prefer logging a non-identifying identifier or omitting the email.
- **Error content in logs (Low):** Some `logger.error(..., {e})` may include stack or DB details. Ensure logs are not exposed to clients; consider sanitizing in production.

---

## 4. API Security

### 4.1 Unauthenticated access (High / Medium)

| Endpoint | Location | Severity | Recommendation |
|----------|----------|----------|----------------|
| `GET /api/v1/matches/` | `matches.py` | **High** | No auth. If matches are not intended to be public, add e.g. `Depends(get_current_active_user)` or a dedicated role. |
| `GET /api/v1/matches/{match_id}` | `matches.py` | **High** | Same; anyone can read any match by ID. Add auth if not public. |
| `GET /api/v1/goals/match/{match_id}` | `goals.py` | Medium | No auth; add auth or document as public. |
| `GET /api/v1/cards/match/{match_id}` | `cards.py` | Medium | Same. |
| `GET /api/v1/substitutions/match/{match_id}` | `substitutions.py` | Medium | Same. |
| `GET /api/v1/news/{news_id}` | `news.py` | Low | May be intentional for public news; add role-based auth if some news is restricted. |

**Action:** Decide whether matches (and related goals/cards/substitutions) are public. If not, add authentication to these GET endpoints.

### 4.2 CORS and middleware

- CORS uses `settings.BACKEND_CORS_ORIGINS` (explicit list); no wildcard `"*"` with credentials.
- Security headers and optional HSTS are set in `main.py`.

### 4.3 IDOR on mutations

- Mutations checked use `current_user` and scope (e.g. referee for match, tournament admin for tournament/team). No obvious IDOR found; continue to verify each “by id” mutation has correct role and resource ownership.

---

## 5. Dependencies

| Package | Version | Finding | Action |
|---------|---------|---------|--------|
| **PyJWT** | 2.11.0 → **≥2.12.0** | CVE-2026-32597: `crit` header not validated (CVSS 7.5). | ✅ `requirements.txt` updated to `PyJWT>=2.12.0`. Run `pip install -U PyJWT` and redeploy. |
| passlib | 1.7.4 | CryptContext with sha256_crypt/bcrypt is acceptable. | Optional: use only bcrypt for new hashes. |
| Others | — | No obviously dangerous patterns. | Run `pip audit` or Snyk/Safety regularly. |

---

## 6. File Operations (Uploads)

- **Path/filename:** Extension is taken from `os.path.splitext(file.filename)[1]`. Stored path is `path = unique_filename` (UUID + extension), so path traversal is limited; sanitizing or ignoring client filename and using a strict extension whitelist is still recommended.
- **Content type:** Validation is by `file.content_type` only; client can lie. Consider validating magic bytes for image type.
- **Error handling:** ✅ Fixed — client no longer receives `str(e)`; generic "Failed to upload image" returned; full error logged server-side.

---

## 7. Error Handling & Information Disclosure

| Location | Issue | Status |
|----------|--------|--------|
| `matches.py` — read_matches, read_match | `traceback.print_exc()` and `detail=str(e)` | ✅ Fixed: generic "Internal Server Error", full traceback only in logs. |
| `uploads.py` | Exception message in response | ✅ Fixed. |
| `users.py` — create_user | Exception message in response | ✅ Fixed. |

**Recommendation:** Consistently return generic messages to clients and log full errors server-side across all endpoints.

---

## 8. Cryptography & HTTPS

- Password hashing: passlib (sha256_crypt, bcrypt) — acceptable.
- JWT: HS256, expiry set, type claim used; algorithm fixed on decode.
- Random: `uuid.uuid4()` for refresh JTI and upload filenames — acceptable.
- HTTPS: If the app is behind a reverse proxy that enforces HTTPS, document it; otherwise consider redirecting HTTP → HTTPS in production.

---

## 9. Health Endpoint

- `GET /health` returns `{"status": "ok", "environment": settings.ENVIRONMENT}`. Low risk (typically "development" or "production"). Avoid returning other env vars or internal URLs.

---

## Checklist for Deployment

- [ ] Run `pip install -U -r requirements.txt` (ensure PyJWT ≥ 2.12.0).
- [ ] Ensure `.env` is never committed; secrets only in environment.
- [ ] Decide auth policy for `GET /matches/`, `GET /matches/{id}`, goals/cards/substitutions by match; add auth if not public.
- [ ] Reduce PII in password-reset and other auth logs if required by policy.
- [ ] Ensure production logs are not exposed to clients and consider log sanitization.
- [ ] Enforce HTTPS at reverse proxy or in app for production.

---

*This audit was generated from a deep code review and automated exploration of the goalup_backend codebase.*
