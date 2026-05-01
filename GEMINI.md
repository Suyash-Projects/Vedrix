# 🤖 System Prompt & Implementation Blueprint: Talent Sync

**Context:** You are an expert AI software engineer. This document is your comprehensive instruction manual and architectural blueprint. If you are given this file and asked to "build the application," you must strictly follow the technical specifications, schemas, directory structures, and implementation phases detailed below to recreate the **Talent Sync AI Interview System** from scratch.

---

## 🎯 1. Project Objective & Core Business Logic

**Project Name:** Talent Sync
**Description:** A sophisticated, full-stack AI-powered interview platform with a dual-sided marketplace approach.
- **B2C (Students):** Users upload resumes, practice unlimited adaptive AI interviews across various tech stacks, and receive detailed analytical feedback to improve skills.
- **B2B (HR Professionals):** Recruiters create "Job Drives," invite candidates, and use the AI as a first-round screener to evaluate technical, communication, and behavioral competencies without bias.

---

## 🛠️ 2. Technology Stack Constraints

You must use **exactly** this stack. Do not introduce React, Vue, Next.js, Django, or alternative databases unless instructed.
- **Backend:** Python 3.8+, Flask, Flask-SQLAlchemy (ORM), Flask-Login (Auth), Flask-Mail.
- **Database:** SQLite (development), structured for easy migration to PostgreSQL.
- **Frontend:** HTML5, Vanilla JavaScript (ES6+), CSS3.
- **UI Framework:** Bootstrap 5.3 (via CDN), Font Awesome 6.
- **AI Integration:** OpenRouter API (utilizing multiple specialized models via HTTP requests).
- **File Processing:** `PyPDF2` (for resume parsing).

---

## 📁 3. Mandatory Directory Structure

You must enforce this application factory pattern structure:

```text
/
├── app.py                     # Production WSGI entry point
├── run.py                     # Development server entry point
├── config.py                  # Environment configurations (Dev/Prod/Test)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
├── app/                       # Main application package
│   ├── __init__.py            # Flask app factory, extension initialization
│   ├── models.py              # SQLAlchemy database models
│   ├── auth.py                # Authentication blueprints (Login/Register)
│   ├── main.py                # Landing pages & general routes
│   ├── ai_service.py          # Core AI logic & OpenRouter integration
│   ├── adaptive_api.py        # Dedicated API endpoints for real-time interview flow
│   ├── student.py             # Student dashboard blueprint
│   ├── hr.py                  # HR dashboard blueprint
│   ├── admin.py               # System admin blueprint
│   └── utils.py               # Helper functions (file uploads, parsing)
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Core layout (navbar, footer, flash messages)
│   ├── index.html             # Landing page
│   ├── auth/                  # login.html, register.html
│   ├── student/               # dashboard.html, analytics.html
│   ├── hr/                    # dashboard.html, create_drive.html, candidates.html
│   └── interview/             # interface.html (The live interview room)
└── static/                    # Public assets
    ├── css/                   # main.css, modern-ui.css
    ├── js/                    # main.js (Vanilla JS logic)
    └── uploads/               # /resumes, /photos (Ensure .gitignore ignores contents)
```

---

## 🗄️ 4. Database Schema (SQLAlchemy)

You must implement these models in `app/models.py` with these exact relationships:

### `User` (flask_login.UserMixin)
- `id` (PK), `email` (Unique), `username` (Unique), `password_hash`, `user_type` ('student', 'hr', 'admin').
- `first_name`, `last_name`, `phone`, `profile_photo`.
- **Relationships:** One-to-One with `StudentProfile` and `HRProfile`. One-to-Many with `InterviewSession`.

### `StudentProfile`
- `id` (PK), `user_id` (FK to User).
- `university`, `degree`, `graduation_year`, `gpa`.
- `skills` (JSON string), `resume_file`, `resume_text` (Parsed PDF content).
- `experience_level` ('fresher', 'experienced').

### `HRProfile`
- `id` (PK), `user_id` (FK to User).
- `company_name`, `department`, `position`, `hr_code` (Unique invite code).
- **Relationships:** One-to-Many with `JobDrive`.

### `JobDrive`
- `id` (PK), `hr_id` (FK to HRProfile).
- `title`, `description`, `job_role`, `experience_required`, `skills_required` (JSON).
- `deadline`, `is_active` (Boolean).
- **Relationships:** One-to-Many with `InterviewSession`.

### `InterviewSession`
- `id` (PK), `candidate_id` (FK to User), `job_drive_id` (FK to JobDrive, nullable for practice).
- `session_type` ('practice', 'actual'), `status` ('scheduled', 'in_progress', 'completed').
- `start_time`, `duration` (Integer seconds).
- `questions` (JSON string of questions asked), `responses` (JSON string of answers).
- `ai_feedback` (JSON string of detailed feedback), `overall_score` (Float).

---

## 🧠 5. The AI Brain (`ai_service.py`)

This is the most critical component. The system does not use static question banks. It must use the **OpenRouter API** to orchestrate specific models for specific tasks.

**Required Model Routing:**
1.  **Question Generation:** `x-ai/grok-4-fast:free` (Requires context: Job Role, Resume parsed text, previous answers).
2.  **Adaptive Follow-ups:** `nvidia/nemotron-nano-9b-v2:free` (Reacts to user text/voice input in real-time).
3.  **Comprehensive Feedback Analysis:** `deepseek/deepseek-chat-v3.1:free` (Analyzes the entire JSON conversation history).
4.  **Code Evaluation (Technical):** `openai/gpt-oss-120b:free` (Evaluates logic and correctness of submitted code).

**Implementation Rules for AI:**
- Must have robust error handling. If OpenRouter fails or returns invalid JSON, the service **must** degrade gracefully to predefined hardcoded fallback questions and feedback structures.
- All AI responses must be strictly coerced into structured JSON (e.g., arrays of question objects with `id`, `type`, `question`, `category`, `difficulty`, `time_limit`).

---

## ⚙️ 6. Core System Workflows

When building, ensure these workflows operate flawlessly:

### A. The Adaptive Interview Flow (The Interface)
1.  **Initialization:** Candidate enters the room. AI generates the first question based on their resume and target role.
2.  **Execution:** JS timer starts. Candidate types or records answer.
3.  **Adaptation:** JS sends answer to `/api/generate-adaptive-question` (`adaptive_api.py`).
4.  **Evaluation Loop:** If the answer is good, AI generates a harder, related follow-up. If poor, AI generates an easier or clarifying question.
5.  **Completion:** After *N* questions or time expiry, session ends. All Q&A pairs are packaged and sent to the Feedback AI model.

### B. The HR Recruitment Flow
1.  HR creates a `JobDrive`.
2.  System generates a unique URL for the drive.
3.  HR shares URL. Students click, register/login, and take the specific interview.
4.  HR dashboard populates with candidates, ranking them by AI-generated `overall_score`.

---

## 🏗️ 7. Step-by-Step Implementation Execution Plan

If instructed to build this system, execute in these exact phases, validating each before moving to the next.

**Phase 1: Environment & Foundation**
- Set up `app.py`, `config.py`, and the Flask application factory in `app/__init__.py`.
- Configure `requirements.txt` and `.env` handling.

**Phase 2: Database & Authentication**
- Implement `app/models.py`.
- Build `app/auth.py` with Flask-Login. Ensure separate registration paths for Students (requires parsing resume) vs. HR (requires company details).

**Phase 3: AI Engine Implementation**
- Build `app/ai_service.py`. Implement the HTTP requests to OpenRouter.
- Write robust prompts requiring JSON outputs. Build the fallback mechanisms.

**Phase 4: API & Interview Logic**
- Build `app/adaptive_api.py`. Create endpoints for:
    - `/api/generate-next-question`
    - `/api/evaluate-code`
- Connect these endpoints to the AI Service.

**Phase 5: User Interfaces (Frontend)**
- Build `base.html` with Bootstrap.
- Build the `student/dashboard.html` and `hr/dashboard.html`.
- Build the critical `interview/interface.html`. Use Vanilla JS to handle media recording, timers, and AJAX calls to the `adaptive_api`.

**Phase 6: Final Polish & Analytics**
- Ensure the Feedback AI properly updates the database.
- Build the post-interview results page displaying metrics (radar charts, strengths/weaknesses).
- Thoroughly test the "Fallback" mode to ensure the app doesn't crash if the AI API is down.

---
**End of Instructions.** You are now ready to construct Talent Sync autonomously.