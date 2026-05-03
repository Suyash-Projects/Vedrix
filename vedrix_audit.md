# Vedrix — Professional AI Interview System Audit
**Full End-to-End Code Review · May 2026**

---

## Executive Summary

Vedrix has a solid foundation with a well-thought-out LangGraph interview engine, a clean dark-theme UI, and a working HR drive/invite system. However, there are **26 critical-to-important issues** across 6 domains that must be resolved before this can be considered production-ready for professional deployment. They are grouped by severity below.

---

## 🔴 CRITICAL — Will Cause Crashes or Data Loss in Production

### 1. `evaluate_answer_node` is Disconnected from the Graph
**File:** `backend/app/services/interview_engine/graph.py` + `nodes.py`

The `evaluate_code_node` function (for coding challenge evaluation) is **defined** in `nodes.py` (line 133) but is **never imported or added** to the LangGraph `StateGraph`. This means when `is_coding_mode = True`, the graph still routes to `evaluate_answer_node` instead of `evaluate_code_node`. Code submissions are silently evaluated as text answers, producing incorrect scores.

```python
# graph.py — MISSING these lines:
from .nodes import ..., evaluate_code_node
workflow.add_node("evaluate_code", evaluate_code_node)
# Also missing: conditional edge to route to evaluate_code when is_coding_mode=True
```

---

### 2. `EvaluationService.generate_final_report` is Synchronous in an Async Context
**File:** `backend/app/services/evaluation_service.py` — Line 54

`self.llm.invoke(...)` (synchronous) is called directly inside an `async` WebSocket handler. This **blocks the entire event loop** for the duration of the API call (could be 5-30 seconds), effectively making the entire server unresponsive while one candidate's report is generated.

```python
# WRONG — blocks the event loop:
response = self.llm.invoke([...])

# CORRECT — must be:
response = await self.llm.ainvoke([...])
```

---

### 3. Resume Text is Hardcoded — AI Has Zero Candidate Context
**File:** `backend/app/api/v1/endpoints/interview.py` — Lines 69-70

For **non-invite (practice) sessions**, the resume is hardcoded:
```python
job_role = "Senior Backend Engineer"
resume_text = "Experienced developer context."
```
The entire adaptive intelligence of the interviewer is disabled for practice sessions. The AI cannot tailor questions to the actual candidate's experience. There is no mechanism to pass job role or resume to the WebSocket endpoint for authenticated practice users.

---

### 4. WebSocket Authentication is Completely Absent
**File:** `backend/app/api/v1/endpoints/interview.py` — Line 49-56

The `/ws/{session_id}` endpoint accepts `user_id` as a plain query parameter with **zero verification**. Any user can impersonate any `user_id` and start a session under another person's account. There is no JWT token validation on the WebSocket handshake.

```python
# Current (insecure):
user_id: Optional[int] = None  # Query param — trust anyone

# Needed: Validate JWT passed as query param or in WebSocket headers
```

---

### 5. `InterviewSession.duration` is Never Calculated
**File:** `backend/app/api/v1/endpoints/interview.py` — Lines 284-290

When marking a session as `completed`, `end_time` is saved but `duration` is never computed. The model has a `duration: Optional[int]` field, but it is always stored as `None`.

```python
# Missing:
session_record.duration = int((datetime.utcnow() - session_record.start_time).total_seconds())
```

---

### 6. `ResumeParser.get_skills_summary` is Synchronous — Blocks Event Loop
**File:** `backend/app/services/resume_service.py` — Line 59

`llm.invoke(...)` called synchronously. This blocks the async FastAPI event loop during every resume upload. Must use `await llm.ainvoke(...)` or run in a thread executor.

---

## 🟠 HIGH — Major Feature Gaps or Wrong Behavior

### 7. Student Dashboard is Effectively a Placeholder
**File:** `frontend/src/App.jsx` — Lines 241-256

The "Student Dashboard" (view `dashboard`) is a single card with no: past session history, resume upload UI, profile editing, skill progress over time, or any data visualization. A student logs in and sees only one "Join Room" button — which has no concept of which drive/role they're joining. This is not a professional student experience.

---

### 8. Resume Upload Has No Frontend Integration
**File:** `backend/app/api/v1/endpoints/resume.py` exists (2870 bytes) but there is **no resume upload UI** in `StudentDashboard` or anywhere in the frontend. Students cannot upload their own resume, so the interview engine has no actual resume context for authenticated users. This directly causes Issue #3.

---

### 9. `submitTextAnswer` Uses `window.prompt()` — Unacceptable UX
**File:** `frontend/src/pages/InterviewRoom.jsx` — Line 243

```javascript
const textInput = prompt("Type your answer here:");
```

Using a browser `prompt()` dialog for text answers in a professional interview platform is completely unacceptable. This breaks the immersive UI, is blocked by many browsers in iframes, and is jarring to candidates.

**Fix:** Add a dedicated `<textarea>` input panel in the InterviewRoom UI.

---

### 10. `Editor` Component Used Without Import in InterviewRoom
**File:** `frontend/src/pages/InterviewRoom.jsx` — Line 371

```jsx
<Editor ... />
```

`Editor` (Monaco Editor) is referenced but **never imported**. This causes a hard React crash the moment coding mode is triggered. The `@monaco-editor/react` package must be installed and imported.

```javascript
// Missing:
import Editor from '@monaco-editor/react';
```

---

### 11. Live Monitoring Tab Shows `candidate_id` (a Number), Not Candidate Name
**File:** `frontend/src/pages/HRDashboard.jsx` — Lines 424-425

```jsx
<p>Session #{session.id}</p>
<p>Candidate #{session.candidate_id}</p>
```

HR users see `Candidate #3`, not the actual candidate's name or email. The backend `/hr/interviews` endpoint does not join with the `User` table to fetch candidate name/email. This data should be enriched server-side.

---

### 12. Token Expiry Uses Naïve `datetime.utcnow()` — Will Break with Python 3.12+
**Files:** `backend/app/api/v1/endpoints/hr.py` — Lines 136, 161; `backend/app/models/interview.py` — Lines 19, 32, 33, 47

`datetime.utcnow()` is deprecated and removed in Python 3.12+. Must use `datetime.now(UTC)` or `datetime.now(timezone.utc)`.

```python
# Wrong (deprecated):
expires_at=datetime.utcnow() + timedelta(hours=72)

# Correct:
from datetime import datetime, timezone
expires_at=datetime.now(timezone.utc) + timedelta(hours=72)
```

---

### 13. `should_continue` in Graph Never Handles the `"closing"` Phase
**File:** `backend/app/services/interview_engine/graph.py` — Lines 7-10

When `current_phase` transitions to `"closing"`, `update_memory_node` sets `interview_complete = True`. However if the LLM then generates one final question in the `generate_question` node, it gets sent to the frontend before the `should_continue` check fires. The candidate receives a question after being told the interview is over.

---

### 14. `hr_instructions` Injection Has No Auth — Any User Can Inject
**File:** `backend/app/api/v1/endpoints/interview.py` — Lines 313-317

```python
@router.post("/sessions/{session_id}/hr-instruction")
async def send_hr_instruction(session_id: str, instruction: Dict[str, str]):
```

This endpoint has **no authentication dependency** (`Depends(deps.get_current_hr)` is absent). Any unauthenticated user who knows a `session_id` can inject arbitrary instructions into a live AI interview session.

---

### 15. `FRONTEND_BASE_URL` is Hardcoded to `localhost`
**File:** `backend/app/api/v1/endpoints/hr.py` — Line 24

```python
FRONTEND_BASE_URL = "http://localhost:5173"
```

Invite links and magic links sent by email will always contain `localhost:5173` regardless of where the system is deployed. Must be moved to `settings.FRONTEND_BASE_URL` in the Pydantic config.

---

## 🟡 MEDIUM — Quality, Scalability & Professionalism Issues

### 16. Silent Error Swallowing — No Proper Logging System
**Files:** Throughout `nodes.py`, `evaluation_service.py`, `voice_service.py`

Exceptions are caught with bare `except Exception` and either silently ignored or logged with `print()`. In production, this means errors are invisible. There is no structured logging (e.g., `logging` module or a service like Sentry). Critical failures in the AI engine return silent fallback values, making debugging impossible.

---

### 17. No Database Migrations — Using Auto-Create Only
**File:** `backend/` — No `alembic/` migrations directory found

`alembic` is in `requirements.txt` but there are no migration files. The system relies on SQLModel's auto-create tables at startup, which means any schema change (new column, new table) requires manual database drops or data loss in production.

---

### 18. `InterviewSession.questions` Column is Unused
**File:** `backend/app/models/interview.py` — Line 50

The model has `questions: Optional[str] = None  # JSON` but it is **never written to** during the interview flow. The generated questions are never persisted, only the `responses` (messages). Post-interview analysis cannot identify which specific questions scored poorly without this data.

---

### 19. `topic_scores` State Key is Defined but Never Used
**File:** `backend/app/services/interview_engine/state.py` — Line 29

```python
topic_scores: Dict[str, float]
```

This field is declared in the `InterviewState` TypedDict but is **never written to** by any node. `update_memory_node` only writes to `topic_strengths`. This represents dead code and a gap in the analytics data model.

---

### 20. Radar Chart Has Duplicate / Incorrect Metrics
**File:** `frontend/src/pages/InterviewReport.jsx` — Lines 62-66

```javascript
{ subject: 'Clarity', A: (aiFeedback?.communication_clarity ?? 0) * 10 },
{ subject: 'Comms', A: (aiFeedback?.communication_clarity ?? 0) * 10 },  // DUPLICATE
{ subject: 'Logic', A: (data.overall_score ?? 0) * 10 }, // Not a metric
```

`Clarity` and `Comms` are mapped to the same value (`communication_clarity`). "Logic" is mapped to `overall_score`, not a separate logic metric. The radar chart shows misleading data.

---

### 21. Proctoring Data is Completely Fake / Hardcoded
**File:** `frontend/src/pages/InterviewReport.jsx` — Lines 256-260

```javascript
{ label: 'Tab Switches', val: '0' },
{ label: 'Eye Tracking', val: '98%' },
{ label: 'Audio Quality', val: 'Excellent' },
```

The "System Integrity" panel shows **hardcoded placeholder data** presented to HR as real proctoring metrics. This is misleading and could lead to incorrect hiring decisions based on fabricated data. Either implement actual tab-switch detection (via `visibilitychange` events) or clearly label this section as "Coming Soon."

---

### 22. No Rate Limiting or Abuse Protection on WebSocket or API
**File:** Entire backend

There is no rate limiting on:
- The WebSocket connection endpoint (anyone can open unlimited sessions)
- The bulk invite endpoint (HR can send unlimited emails)
- The auth endpoints (no brute-force protection on login)

This is a significant risk in any production deployment.

---

### 23. `drive_title` in `"closing"` Phase Condition Bug
**File:** `backend/app/services/interview_engine/nodes.py` — Line 205

```python
elif curr_phase == "behavioral" and idx >= 11:
    new_phase = "closing"
```

But `max_questions` defaults to 12 (line 177 of `interview.py`). At `idx >= 11`, the phase becomes `"closing"` AND `interview_complete` becomes `True` at `idx >= 12`. This means question 12 is generated in `"closing"` phase — but there is no prompt guidance for the `"closing"` phase in `generate_question_node` (the system prompt only handles warmup/technical/stress/behavioral). The AI gets no instructions for how to conduct a closing statement.

---

### 24. `StudentDashboard` Has No Route in `App.jsx` — Uses Inline JSX
**File:** `frontend/src/App.jsx` — Lines 241-256

The student view is defined inline within `App.jsx` instead of using the dedicated `StudentDashboard.jsx` file. The `StudentDashboard.jsx` page (14 KB) is **imported but never rendered**. This is dead code.

---

## 🔵 LOW — Polish & Code Quality

### 25. Typo on Landing Page CTA
**File:** `frontend/src/App.jsx` — Line 107

```jsx
<span>Start Evaluaton</span>  {/* Missing 'i' */}
```

Should be "Start Evaluation."

---

### 26. Magic Link Generation Doesn't Associate `candidate_email`
**File:** `backend/app/api/v1/endpoints/hr.py` — Lines 132-141

The single-use magic link endpoint (`/drives/{drive_id}/magic-link`) creates a `DriveInviteToken` with **no `candidate_email`**. This means when a candidate uses this generic link, `candidate_email` is `None`, the shadow user gets a `None`-based username, and emails cannot be sent. The link is effectively anonymous and untraceable. Only the bulk-invite endpoint correctly associates emails.

---

## Summary Table

| # | Severity | Domain | Issue |
|---|----------|--------|-------|
| 1 | 🔴 Critical | AI Engine | `evaluate_code_node` not in graph |
| 2 | 🔴 Critical | Backend | `generate_final_report` blocks event loop |
| 3 | 🔴 Critical | AI Engine | Resume hardcoded for practice sessions |
| 4 | 🔴 Critical | Security | WebSocket has no authentication |
| 5 | 🔴 Critical | Data | `duration` never calculated |
| 6 | 🔴 Critical | Backend | Resume skill extraction blocks event loop |
| 7 | 🟠 High | Frontend | Student dashboard is a placeholder |
| 8 | 🟠 High | Feature | No resume upload UI |
| 9 | 🟠 High | UX | `window.prompt()` for text answers |
| 10 | 🟠 High | Frontend | Monaco Editor not imported — crashes |
| 11 | 🟠 High | Frontend | Live monitoring shows IDs, not names |
| 12 | 🟠 High | Backend | `datetime.utcnow()` deprecated |
| 13 | 🟠 High | AI Engine | Closing phase sends extra question |
| 14 | 🟠 High | Security | HR instruction endpoint has no auth |
| 15 | 🟠 High | Config | Frontend URL hardcoded to localhost |
| 16 | 🟡 Medium | Quality | No logging / all errors silently swallowed |
| 17 | 🟡 Medium | DevOps | No database migrations (Alembic) |
| 18 | 🟡 Medium | Data | `questions` column never written |
| 19 | 🟡 Medium | Data | `topic_scores` state key unused |
| 20 | 🟡 Medium | Frontend | Radar chart has duplicate/fake metrics |
| 21 | 🟡 Medium | Frontend | Proctoring data is hardcoded/fake |
| 22 | 🟡 Medium | Security | No rate limiting anywhere |
| 23 | 🟡 Medium | AI Engine | No closing phase prompt in system prompt |
| 24 | 🟡 Medium | Frontend | `StudentDashboard.jsx` is dead code |
| 25 | 🔵 Low | UX | Typo: "Evaluaton" |
| 26 | 🔵 Low | Feature | Single magic link has no email association |

---

## Recommended Fix Priority Order

**Sprint 1 — Stabilize Core (Fix before any user testing)**
1. Fix `evaluate_code_node` graph wiring (#1)
2. Fix `generate_final_report` to use `ainvoke` (#2)
3. Add WebSocket JWT validation (#4)
4. Fix HR instruction endpoint auth (#14)
5. Import Monaco Editor (#10)
6. Replace `window.prompt()` with textarea (#9)
7. Fix `datetime.utcnow()` deprecation (#12)

**Sprint 2 — Complete the Feature Set**
8. Build Resume Upload UI + connect to practice session WebSocket (#3, #8)
9. Build proper Student Dashboard using `StudentDashboard.jsx` (#7, #24)
10. Persist `questions` + `duration` + `topic_scores` (#5, #18, #19)
11. Fix radar chart metrics (#20)
12. Move `FRONTEND_BASE_URL` to env config (#15)

**Sprint 3 — Production Hardening**
13. Add structured logging (Python `logging` + request IDs) (#16)
14. Set up Alembic migrations (#17)
15. Add rate limiting (FastAPI `slowapi`) (#22)
16. Replace fake proctoring data or clearly label as Coming Soon (#21)
17. Fix closing phase prompt + graph (#13, #23)
18. Enrich live monitoring with candidate names (#11)
19. Fix magic link email association (#26)
20. Fix "Evaluaton" typo (#25)
