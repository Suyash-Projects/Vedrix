# Vedrix Development Report

---

## 📝 Project Overview

**Vedrix** is a highly scalable, AI-powered adaptive interview platform. This project represents a complete architectural migration from a legacy monolithic Flask application (in `/reference`) to a modern, decoupled full-stack system.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 8, JavaScript (JSX), Tailwind CSS v4, Lucide-React, Zustand, Axios |
| **Backend** | FastAPI (Python), SQLModel (SQLAlchemy + Pydantic v2), JWT (python-jose), Passlib/bcrypt |
| **Database** | SQLite + `aiosqlite` (async, zero-config local dev); architected for PostgreSQL in production |
| **AI Infrastructure** | LangGraph (stateful adaptive engine), LangChain-Groq, LangChain-OpenAI, OpenRouter fallback |
| **PDF Parsing** | PyMuPDF (`fitz`) |
| **Dev Runner** | Unified `run_dev.py` using `subprocess` (starts both services concurrently) |

---

## 📂 Directory Structure

```
/
├── Vedrix/                        # Active development directory
│   ├── backend/                   # FastAPI application
│   │   ├── main.py                # App entry point, CORS, router registration
│   │   ├── requirements.txt       # All Python dependencies (pinned)
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── deps.py        # JWT auth dependency injection
│   │   │   │   └── v1/
│   │   │   │       ├── __init__.py          # Central APIRouter
│   │   │   │       └── endpoints/
│   │   │   │           ├── auth.py          # POST /register, POST /login
│   │   │   │           ├── users.py         # GET /users/me
│   │   │   │           └── profiles.py      # POST /profiles/student, POST /profiles/hr
│   │   │   ├── core/
│   │   │   │   ├── config.py      # Pydantic Settings (reads .env)
│   │   │   │   └── security.py    # JWT creation, bcrypt hashing
│   │   │   ├── db/
│   │   │   │   └── session.py     # Async engine, sessionmaker, init_db()
│   │   │   ├── models/
│   │   │   │   ├── user.py        # User SQLModel
│   │   │   │   ├── profile.py     # StudentProfile, HRProfile SQLModels
│   │   │   │   └── interview.py   # JobDrive, InterviewSession SQLModels
│   │   │   ├── schemas/
│   │   │   │   └── user.py        # Pydantic schemas: UserCreate, UserRead, Token, TokenPayload
│   │   │   └── services/
│   │   │       ├── resume_service.py          # PDF text extraction via PyMuPDF
│   │   │       └── interview_engine/
│   │   │           ├── state.py               # InterviewState TypedDict (LangGraph)
│   │   │           ├── providers.py           # LLM provider factories (Groq, NVIDIA, OpenRouter)
│   │   │           ├── nodes.py               # LangGraph nodes: generate, evaluate, update_memory
│   │   │           └── graph.py               # StateGraph definition and compilation
│   ├── frontend/                  # React application
│   │   ├── src/
│   │   │   ├── main.jsx           # React root mount
│   │   │   ├── App.jsx            # Root component: routing, views, Navbar, Dashboard
│   │   │   ├── index.css          # Global styles, Inter font, Tailwind import, animations
│   │   │   ├── pages/
│   │   │   │   ├── Login.jsx      # Login form (wired to Zustand auth store)
│   │   │   │   └── Register.jsx   # Registration form with Student/HR role selector
│   │   │   ├── store/
│   │   │   │   └── useAuthStore.js  # Zustand: login, register, logout, checkAuth, clearError
│   │   │   └── services/
│   │   │       └── api.js          # Axios instance with base URL + Bearer token interceptor
│   └── run_dev.py                 # Unified dev runner
├── reference/                     # Legacy Flask app (reference only, do not modify)
└── .env                           # Root env (legacy Flask vars — not used by FastAPI)
```

---

## ✅ Completed Milestones

### Phase 1 — Infrastructure & Scaffolding
- Initialized **Vedrix** as the active development directory.
- Configured **FastAPI** backend with virtual environment and all dependencies.
- Configured **React (Vite + Tailwind CSS v4)** frontend.
- Created **unified dev runner** (`Vedrix/run_dev.py`) for concurrent startup.
- Docker Compose scaffolded for future orchestration.

### Phase 2 — Database, Auth & Core Services
- Ported all domain models to **SQLModel**: `User`, `StudentProfile`, `HRProfile`, `JobDrive`, `InterviewSession`.
- Implemented **async SQLite** via `aiosqlite`; tables auto-created on startup.
- Built **JWT authentication** system: stateless, HS256-signed tokens.
- Created RESTful endpoints: `POST /register`, `POST /login`, `GET /users/me`, `POST /profiles/student`, `POST /profiles/hr`.

### Phase 3 — AI Engine Scaffolding (LangGraph)
- Defined `InterviewState` TypedDict (tracks messages, difficulty, topic strengths, question index).
- Scaffolded three LangGraph nodes: `generate_question`, `evaluate_answer`, `update_memory`.
- Wired adaptive difficulty: score > 0.7 → harder; score < 0.7 → easier.
- Configured LLM provider factories: **Groq** (fast, `llama-3.1-8b-instant`) and **NVIDIA** (strong, `llama-3.1-405b-instruct`), with **OpenRouter** as fallback.

### Phase 4 — Frontend UI
- Built professional landing page with animated gradient hero heading and feature cards.
- Integrated Login & Register forms with full Zustand state management.
- Added role-aware **Dashboard placeholder** (Student vs HR-specific content).
- Auth flow: Register → redirects to Login → Login → redirects to Dashboard.

---

## 🐛 Bugs Fixed (2026-05-02 — Debug Session)

| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `app/api/deps.py` | `status.HTTP_03_FORBIDDEN` — invalid constant, would crash every protected route | Changed to `status.HTTP_403_FORBIDDEN` |
| 2 | `app/services/resume_service.py` | `from typing import str` — `str` is a Python builtin, not from `typing`; causes `ImportError` | Removed invalid import; added `Optional, List` |
| 3 | `app/services/resume_service.py` | `extract_text` declared `async` but `fitz.open()` is synchronous; misleading type contract | Changed to regular `def` |
| 4 | `app/services/interview_engine/providers.py` | `model_name=` kwarg invalid for `ChatGroq` and `ChatOpenAI` in langchain v0.2+ | Changed both to `model=` |
| 5 | `app/services/interview_engine/graph.py` | Missing edge `generate_question → evaluate_answer`; graph was disconnected after first node | Added `workflow.add_edge("generate_question", "evaluate_answer")` |
| 6 | `app/api/v1/endpoints/profiles.py` | Used deprecated Pydantic v1 `.dict()` method (Pydantic v2 raises a deprecation warning) | Changed both calls to `.model_dump()` |
| 7 | `frontend/src/index.css` | Vite default CSS set dark background (`#242424`) + white text; completely broke the white Tailwind UI | Replaced with `color-scheme: light`, white background, proper text color |
| 8 | `frontend/src/index.css` | `animate-gradient` keyframe referenced in `App.jsx` hero heading but never defined | Added `@keyframes gradient` + `.animate-gradient` class |
| 9 | `frontend/src/index.css` | `@import url(google fonts)` appeared after `@import "tailwindcss"` — violates CSS spec, caused build warning | Moved Google Fonts `@import` to line 1 |
| 10 | `frontend/src/store/useAuthStore.js` | No way to clear error between view switches — error from failed login bled into Register form | Added `clearError` action; `logout` now also clears error |
| 11 | `frontend/src/App.jsx` | After successful login, redirected back to `'landing'` instead of a dashboard | Added `'dashboard'` view state; post-login routes to Dashboard |
| 12 | `frontend/src/App.jsx` | `clearError` not called when switching views — stale errors persisted | All view switches go through `switchView()` which calls `clearError()` |
| 13 | `app/core/config.py` | `ALGORITHM` was a local constant in `security.py` only; not accessible from config | Added `ALGORITHM: str = "HS256"` to `Settings`; `security.py` re-exports it for backwards compatibility |

---

## 🧪 Verification Results (2026-05-02)

All tests run against `http://127.0.0.1:8000`.

| Test | Method | Endpoint | Result |
|---|---|---|---|
| User registration | `POST` | `/api/v1/auth/register` | ✅ 200 — returns `id, email, username, user_type` |
| User login | `POST` | `/api/v1/auth/login` | ✅ 200 — returns signed JWT `access_token` |
| Protected user profile | `GET` | `/api/v1/users/me` | ✅ 200 — returns full user object |
| Frontend build | `npm run build` | — | ✅ 0 errors, 0 warnings |
| API docs | `GET` | `/docs` | ✅ Swagger UI loads with all 6 routes registered |

---

## 📍 Current Status

**Stable Functional Core** — Backend and frontend are both fully operational with no outstanding runtime errors.

- ✅ Register / Login / JWT auth flow — end-to-end verified
- ✅ Frontend builds clean (0 errors, 0 warnings)
- ✅ Dashboard placeholder rendered based on `user_type` (Student vs HR)
- ✅ LangGraph engine scaffolded with correct edges and adaptive logic
- ⬜ LLM nodes still use mock responses (no real API calls yet)
- ⬜ Resume upload endpoint not yet wired
- ⬜ WebSocket interview room not yet built

---

## 🚀 Recommended Next Steps (Phase 3 Onwards)

### Priority 1 — Real AI Integration
1. In `nodes.py`, replace mock responses with actual `llm.invoke(prompt)` calls using the Groq/NVIDIA providers.
2. Use LangChain's `JsonOutputParser` to enforce structured JSON output from the LLM.
3. Add fallback: if `get_fast_llm()` fails → call `get_fallback_llm()` automatically.

### Priority 2 — Resume Upload
1. Add `POST /api/v1/profiles/student/resume` endpoint accepting `multipart/form-data`.
2. Save file to disk, call `ResumeParser.extract_text(path)`, store result in `StudentProfile.resume_text`.

### Priority 3 — WebSocket Interview Room
1. Add `ws://localhost:8000/api/v1/interview/ws/{session_id}` WebSocket endpoint.
2. On connect: initialize `InterviewState`, call `interview_graph.invoke(state)` to get first question.
3. On message (user answer): feed answer back into graph at `evaluate_answer` node.
4. Stream back `next_question` JSON to the frontend.
5. Build `InterviewRoom.jsx` page in frontend using native WebSocket API.

### Priority 4 — Feedback & Analytics
1. On session complete, send full Q&A history to `deepseek/deepseek-chat-v3-1:free` via OpenRouter.
2. Store returned feedback JSON in `InterviewSession.ai_feedback` and `overall_score`.
3. Build `Results.jsx` page with radar charts (use `recharts` library).

### Priority 5 — HR Job Drives
1. Add CRUD endpoints for `JobDrive` model.
2. Generate a unique invite URL per drive (use `uuid` + a short slug).
3. HR dashboard: list drives, show candidates ranked by `overall_score`.

---

## ⚙️ How to Run (Developer Setup)

### Option A — Unified Runner
```bash
cd Vedrix
python run_dev.py
```
Starts both backend (port 8000) and frontend (port 5173) concurrently.

### Option B — Manually

**Backend:**
```bash
cd Vedrix/backend
venv/Scripts/activate        # Windows
# or: source venv/bin/activate  # macOS/Linux
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd Vedrix/frontend
npm install    # first time only
npm run dev
```

URLs:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

### Environment
Ensure `Vedrix/backend/.env` exists with all API keys. See `.env.example` at root for the required variables. The important ones are:
```
GROQ_API_KEY=gsk_...
NVIDIA_API_KEY=nvapi-...
OPENROUTER_API_KEY=sk-or-v1-...
SECRET_KEY=<strong random string for production>
DATABASE_URL=sqlite+aiosqlite:///./vedrix.db
```

---

*Report last updated: 2026-05-02 by Antigravity (AI assistant) — Debug & Stabilization session.*
