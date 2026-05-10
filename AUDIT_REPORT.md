# Vedrix AI Interview System - End-to-End Audit Report

**Date:** 2026-05-10  
**Auditor:** Claude Code  
**Version:** 1.0.0

---

## Executive Summary

This audit covers the Vedrix AI Interview System, a dual-sided platform (B2C candidates + B2B recruiters) built with FastAPI + React + SQLite + LangGraph. The application has a solid foundation but has several security, performance, and code quality issues that should be addressed.

**Overall Risk Level:** 🟡 MEDIUM

| Category | Count | Severity |
|----------|-------|----------|
| Critical | 2 | 🔴 |
| High | 5 | 🟠 |
| Medium | 8 | 🟡 |
| Low | 6 | 🟢 |

---

## 1. Security Issues

### 1.1 CRITICAL: Hardcoded Fallback Secret Key

**Location:** `Vedrix/backend/app/core/config.py:11`

```python
SECRET_KEY: str = "change-me-in-production-use-env-file"
```

**Issue:** The default secret key is hardcoded. If `.env` file is missing or not properly loaded, the application falls back to this weak default, allowing JWT token forgery.

**Impact:** Attackers can forge authentication tokens and impersonate any user, including admins.

**Recommendation:**
```python
SECRET_KEY: str = ""  # Require env var, fail fast if missing
```

---

### 1.2 HIGH: No Password Strength Validation

**Location:** `Vedrix/backend/app/schemas/user.py`

**Issue:** No minimum length, complexity requirements, or rate limiting on registration endpoint.

**Impact:** Attackers can brute-force or use weak passwords.

**Recommendation:** Add password validation schema:
```python
class UserCreate(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)
    # Add regex for complexity: uppercase, lowercase, number, special
```

---

### 1.3 HIGH: WebSocket Authentication Gap

**Location:** `Vedrix/backend/app/api/v1/endpoints/interview.py:68-76`

```python
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    drive_id: Optional[int] = None,
    token: Optional[str] = None,  # Optional - can be None
    auth_token: Optional[str] = None,  # Optional - can be None
```

**Issue:** WebSocket accepts connections without required authentication. Both `token` and `auth_token` are optional, allowing unauthenticated access.

**Impact:** Anonymous users can access interview sessions and potentially enumerate session IDs.

**Recommendation:** Require authentication token for all WebSocket connections.

---

### 1.4 HIGH: No Rate Limiting on Auth Endpoints

**Location:** `Vedrix/backend/app/api/v1/endpoints/auth.py`

**Issue:** Login and registration endpoints have no rate limiting.

**Impact:** Vulnerable to brute-force attacks on login and email enumeration on registration.

**Recommendation:**
```python
@router.post("/login")
@limiter.limit("5/minute")
async def login(...):
```

---

### 1.5 MEDIUM: Admin Role Validation Gap

**Location:** `Vedrix/backend/app/api/v1/endpoints/admin.py:180-185`

```python
body: dict,  # Expects {"role": "student"|"hr"|"admin"}
role = body.get("role")
if role not in ("student", "hr", "admin"):
```

**Issue:** Uses loose `dict` type instead of Pydantic schema. No validation prevents extra fields.

**Recommendation:** Use Pydantic model:
```python
class RoleChangeRequest(BaseModel):
    role: Literal["student", "hr", "admin"]
```

---

### 1.6 MEDIUM: CORS Allows All Origins in Dev

**Location:** `Vedrix/backend/main.py:40-51`

```python
allow_origins=[
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
],
```

**Issue:** Hardcoded localhost ports plus settings. Should be more restrictive in production.

**Recommendation:** Use environment-based allowed origins list.

---

### 1.7 LOW: Token Stored in localStorage

**Location:** `Vedrix/frontend/src/store/useAuthStore.js:25`

```javascript
localStorage.setItem('token', access_token);
```

**Issue:** XSS vulnerability - tokens in localStorage are accessible to JavaScript.

**Impact:** If XSS exists, attacker can steal tokens.

**Recommendation:** Consider httpOnly cookies for token storage.

---

## 2. Backend Issues

### 2.1 CRITICAL: Broad Exception Handling Masks Errors

**Location:** `Vedrix/backend/app/api/v1/endpoints/interview.py:410-413`

```python
except Exception as e:
    logger.error(f"WebSocket fatal error [{session_id}]: {e}")
    traceback.print_exc()
    await manager.send_json({"type": "error", "data": str(e)}, session_id)
```

**Issue:** Catches all exceptions and exposes raw error messages to client.

**Impact:** Information leakage - internal paths, variable names, database errors exposed.

**Recommendation:** Return generic error message, log details server-side.

---

### 2.2 HIGH: Hardcoded Default Job Role

**Location:** `Vedrix/backend/app/api/v1/endpoints/interview.py:90-91`

```python
job_role = "Software Engineer"
resume_text = "General software engineering background."
```

**Issue:** Default values used when no drive is specified - leads to generic interviews.

**Impact:** Poor interview quality for practice sessions without profile data.

---

### 2.3 HIGH: N+1 Query Problem in Admin Dashboard

**Location:** `Vedrix/backend/app/api/v1/endpoints/admin.py:319-372`

```python
for drive in drives:
    # Each iteration makes 3+ additional queries
    hr_res = await db.execute(select(HRProfile).where(HRProfile.id == drive.hr_id))
    hr_user_res = await db.execute(select(User).where(User.id == hr_profile.user_id))
    sessions_res = await db.execute(select(InterviewSession)...)
    tokens_res = await db.execute(select(DriveInviteToken)...)
```

**Issue:** List all drives makes O(n) database queries where n = number of drives.

**Impact:** Performance degrades with scale. 100 drives = 400+ queries.

**Recommendation:** Use JOIN queries or eager loading.

---

### 2.4 HIGH: No Pagination on List Endpoints

**Location:** Multiple admin/hr endpoints

```python
result = await db.execute(select(User))  # Returns ALL users
result = await db.execute(select(InterviewSession))  # Returns ALL sessions
```

**Issue:** No limit/offset or cursor-based pagination.

**Impact:** Memory exhaustion with large datasets, slow response times.

**Recommendation:** Add pagination params:
```python
@router.get("/users")
async def read_users(
    limit: int = 20,
    offset: int = 0,
):
```

---

### 2.5 MEDIUM: Division by Zero in Score Calculation

**Location:** `Vedrix/backend/app/api/v1/endpoints/admin.py:348-350`

```python
avg_score = (
    round(sum(s.overall_score for s in completed) / len(completed), 1)
    if completed else None
)
```

**Issue:** If `completed` list has sessions with `overall_score=None`, this will fail or give NaN.

**Impact:** Potential server error when calculating averages.

---

### 2.6 MEDIUM: No Transaction Rollback Handling

**Location:** `Vedrix/backend/app/api/v1/endpoints/auth.py:68-79`

```python
try:
    await db.flush()
except Exception as e:
    await db.rollback()
    # Re-check which constraint failed
```

**Issue:** After rollback, session may be in inconsistent state. Manual constraint checking is error-prone.

**Recommendation:** Use database-level unique constraints and handle specific integrity errors.

---

### 2.7 MEDIUM: WebSocket Connection Leak

**Location:** `Vedrix/backend/app/api/v1/endpoints/interview.py:56`

```python
manager = ConnectionManager()  # Single global instance
```

**Issue:** If disconnect happens before cleanup, connection reference may persist.

**Impact:** Memory leak over time, especially with unstable connections.

---

### 2.8 LOW: Missing Input Sanitization

**Location:** Various endpoints accept user input without sanitization

**Issue:** Names, company names, etc. accepted as-is.

**Impact:** Potential for injection in PDF generation or email templates.

---

### 2.9 LOW: Unused Supabase Client Import

**Location:** `Vedrix/backend/app/api/v1/endpoints/hr.py:26`

```python
from app.db.supabase_client import supabase_client
```

**Issue:** Imported but only used conditionally (fire-and-forget sync). Unused if Supabase not configured.

---

## 3. Frontend Issues

### 3.1 HIGH: No Global Error Handling for 401

**Location:** `Vedrix/frontend/src/services/api.js`

**Issue:** No interceptor to handle expired tokens and auto-logout.

**Impact:** User sees error messages instead of being redirected to login.

**Recommendation:**
```javascript
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      authStore.logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

### 3.2 MEDIUM: No Token Expiration Handling

**Location:** `Vedrix/frontend/src/store/useAuthStore.js`

**Issue:** Token stored but expiration not checked. Long-lived tokens (8 days) can cause issues.

**Impact:** User may be logged in past token expiration, causing random failures.

---

### 3.3 MEDIUM: Race Condition in Auth Check

**Location:** `Vedrix/frontend/src/store/useAuthStore.js:66-79`

```javascript
checkAuth: async () => {
  const token = localStorage.getItem('token');
  if (!token) { ... }
  set({ isLoading: true });
  try {
    const response = await apiClient.get('/users/me');
    set({ user: response.data, ... });
  } catch { ... }
}
```

**Issue:** Multiple concurrent `checkAuth` calls can cause race conditions.

---

### 3.4 LOW: Hardcoded Fallback API URL

**Location:** `Vedrix/frontend/src/services/api.js:3`

```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
```

**Issue:** Fallback to localhost in production could cause issues.

---

### 3.5 LOW: No Loading State in Components

**Location:** Various page components

**Issue:** Some pages don't show loading indicators during data fetch.

**Impact:** Poor UX - users don't know if something is loading.

---

## 4. Configuration & Deployment Issues

### 4.1 HIGH: Database URL Auto-Fix is a Code Smell

**Location:** `Vedrix/backend/app/core/config.py:56-63`

```python
if settings.DATABASE_URL.startswith("sqlite://"):
    # Auto-fix silently
    settings.DATABASE_URL = settings.DATABASE_URL.replace(...)
```

**Issue:** Silently changing configuration at runtime. Should fail fast if config is wrong.

**Recommendation:** Remove auto-fix, require correct URL in env.

---

### 4.2 MEDIUM: Email Credentials in Environment

**Location:** `Vedrix/backend/app/core/config.py:32-36`

```python
MAIL_USERNAME: str = ""
MAIL_PASSWORD: str = ""
```

**Issue:** Empty defaults mean email service silently fails if not configured.

**Impact:** Users don't know why emails aren't being sent.

---

### 4.3 LOW: Judge0 API Key Optional

**Location:** `Vedrix/backend/app/core/config.py:40-41`

```python
JUDGE0_URL: str = "https://judge0-ce.p.rapidapi.com"
JUDGE0_API_KEY: str = ""
```

**Issue:** Code execution will fail if not configured, but no clear error.

---

## 5. Data Integrity Issues

### 5.1 MEDIUM: No Cascade Delete for Interview Sessions

**Location:** JobDrive deletion in admin.py and hr.py

**Issue:** Sessions manually deleted before drive deletion. If deletion fails mid-way, data becomes inconsistent.

**Recommendation:** Use SQLAlchemy cascade="all, delete-orphan" in models.

---

### 5.2 LOW: No Unique Constraint on HR Code

**Location:** `Vedrix/backend/app/models/profile.py`

**Issue:** If HR codes are generated, no database-level uniqueness guarantee.

---

### 5.3 LOW: NaN Handling in Skill Matrix

**Location:** Interview report generation

**Issue:** If no questions answered, skill scores may be NaN/null.

---

## 6. Performance Issues

### 6.1 MEDIUM: Synchronous PDF Generation

**Location:** `Vedrix/backend/app/services/pdf_service.py`

**Issue:** Though wrapped in `asyncio.to_thread`, PDF generation is CPU-intensive.

**Impact:** Can block event loop under load.

---

### 6.2 LOW: No Database Connection Pooling Config

**Location:** SQLite default configuration

**Issue:** SQLite doesn't support connection pooling, but no max connections configured for production DB.

---

## 7. Summary & Recommendations

### Priority Actions (Immediate)

1. **Fix hardcoded SECRET_KEY** - Use environment variable only
2. **Add WebSocket authentication** - Require token for all connections
3. **Add rate limiting to auth endpoints** - Prevent brute force
4. **Add global 401 handling in frontend** - Auto-logout on token expiry

### Short-term (1-2 weeks)

1. Add password strength validation
2. Implement pagination on list endpoints
3. Fix N+1 queries in admin dashboard
4. Add proper error handling (don't expose raw errors)
5. Add pagination to HR endpoints

### Medium-term (1 month)

1. Replace localStorage with httpOnly cookies
2. Add input sanitization
3. Add database-level cascade deletes
4. Implement proper connection management
5. Add comprehensive test coverage

### Code Quality

1. Remove auto-fix for database URL
2. Use Pydantic models instead of `dict` for request bodies
3. Add type hints where missing
4. Add docstrings to public functions

---

## Appendix: File Reference

| File | Issues Found |
|------|-------------|
| `Vedrix/backend/app/core/config.py` | #1.1, #4.1, #4.2, #4.3 |
| `Vedrix/backend/app/core/security.py` | None |
| `Vedrix/backend/app/api/v1/endpoints/auth.py` | #1.4, #2.6 |
| `Vedrix/backend/app/api/v1/endpoints/admin.py` | #1.5, #2.3, #2.4, #2.5 |
| `Vedrix/backend/app/api/v1/endpoints/hr.py` | #2.9 |
| `Vedrix/backend/app/api/v1/endpoints/interview.py` | #1.3, #2.1, #2.2, #2.7 |
| `Vedrix/frontend/src/services/api.js` | #3.1, #3.4 |
| `Vedrix/frontend/src/store/useAuthStore.js` | #1.7, #3.2, #3.3 |

---

*End of Audit Report*