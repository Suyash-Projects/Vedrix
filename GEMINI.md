# 🤖 Vedrix: Agentic AI Interview Platform

Vedrix is a high-fidelity, agentic AI interview system designed to conduct structured, adaptive interviews using multi-agent orchestration. It features real-time WebSocket communication, voice intelligence, and a professional candidate/HR dashboard.

## 🏗️ Architectural Overview

### Backend (FastAPI)
- **Framework:** FastAPI with asynchronous I/O.
- **Orchestration:** LangGraph for multi-agent workflows (Interviewer, Evaluator, Decision, Memory).
- **Database:** SQLModel (SQLAlchemy) with `aiosqlite` or `asyncpg`.
- **Real-time:** WebSockets for live interview rooms.
- **AI Services:** OpenRouter (NVIDIA Nemotron, GPT-4), Groq (Whisper V3 for STT), DeepSeek (Deep Feedback).

### Frontend (React)
- **Framework:** React 19 (Vite) + TypeScript.
- **Styling:** Tailwind CSS v4, Framer Motion for animations.
- **State Management:** Zustand, React Query.
- **UI Components:** Lucide-React icons, Monaco Editor for coding tasks, Recharts for analytics.

## 📁 Directory Structure

- `Vedrix/backend/`: FastAPI application.
  - `app/api/`: Versioned API endpoints (v1).
  - `app/services/interview_engine/`: LangGraph agent logic.
  - `app/models/`: SQLModel data definitions.
  - `app/db/`: Database session and migration logic.
- `Vedrix/frontend/`: React application.
  - `src/pages/`: Main views (InterviewRoom, Dashboards).
  - `src/components/`: Reusable UI elements.
  - `src/hooks/`: Custom hooks for Auth, MediaRecorder.
- `Design/`: UI/UX design assets and reference images.
- `Prototype/`: Early experimental versions.

## 🚀 Building and Running

### The Intelligent Launcher (Recommended)
The project includes a runner script that handles dynamic ports and synchronizes the frontend environment.
```powershell
python Vedrix/run_dev.py
```

### Manual Backend Setup
```powershell
cd Vedrix/backend
python -m venv venv
./venv/Scripts/activate  # or source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Manual Frontend Setup
```powershell
cd Vedrix/frontend
npm install
npm run dev
```

## 🧠 AI Strategy & Mandates

1.  **Low Latency (Groq):** Use Groq for real-time transcription (Whisper) and fast conversational turns.
2.  **Deep Analysis (DeepSeek/GPT-4):** Use larger models for post-interview evaluation and feedback.
3.  **Asynchronous First:** All backend calls to LLMs and Databases MUST be `async`.
4.  **Type Safety:** Strict Pydantic validation for all API schemas.

## 🎨 Design Tokens (Vedrix Design System)
- **Theme:** Dark, glassy interface (`#020617`).
- **Accent:** Purple (`#7C3AED`).
- **Typography:** Inter (sans-serif).
- **Motion:** Subtle Framer Motion transitions for a "living" feel.

## 🛠️ Development Conventions

- **Code Style:** PEP 8 for Python, Prettier/ESLint for JS/TS.
- **Git Flow:** Use descriptive commit messages (e.g., `feat: add magic link invitation system`).
- **Testing:**
  - Backend: `pytest` in `Vedrix/backend/tests`.
  - Frontend: `vitest` in `Vedrix/frontend`.
- **Migrations:** Use Alembic for database schema changes (`alembic revision --autogenerate`).

## 📍 Roadmap & Next Steps
- [ ] Complete Voice Integration (TTS via OpenAI/Coqui).
- [ ] Implement HR Takeover UI in WebSocket rooms.
- [ ] Generate Post-Interview PDF Reports with Radar Charts.
- [ ] Enhance Proctoring with automated violation detection.
