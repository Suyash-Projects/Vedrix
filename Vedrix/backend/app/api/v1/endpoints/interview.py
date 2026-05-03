from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
import json
import asyncio
import logging
import traceback
from app.core.rate_limit import limiter

from jose import jwt, JWTError
from sqlalchemy import select

from app.core.config import settings
from app.core.security import ALGORITHM
from app.services.interview_engine.graph import interview_graph
from app.services.interview_engine.state import InterviewState
from app.services.voice_service import voice_service
from app.services.evaluation_service import evaluation_service
from app.services.code_execution_service import code_execution_service
from app.services.email_service import (
    send_interview_started_email,
    send_report_to_candidate,
    send_report_to_hr,
)
from app.models.interview import InterviewSession, DriveInviteToken, JobDrive
from app.models.profile import HRProfile, StudentProfile
from app.models.user import User
from app.db.session import async_session
from app.api import deps

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_json(self, message: Dict[str, Any], session_id: str):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(session_id)


manager = ConnectionManager()


def _verify_ws_token(token: str) -> Optional[int]:
    """Validate a JWT passed as a WebSocket query param. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except (JWTError, Exception):
        return None


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    drive_id: Optional[int] = None,
    token: Optional[str] = None,
    auth_token: Optional[str] = None,  # JWT for authenticated practice sessions
):
    await manager.connect(websocket, session_id)
    config = {"configurable": {"thread_id": session_id}}
    db_session_id: Optional[int] = None
    session_start = datetime.now(timezone.utc)

    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    hr_email: Optional[str] = None
    hr_name: Optional[str] = None
    drive_title: Optional[str] = None

    try:
        # ── 1. Determine Context ──────────────────────────────────────────
        job_role = "Software Engineer"
        resume_text = "General software engineering background."

        if drive_id and token:
            # ── Guest / Invite flow ──
            async with async_session() as db:
                result = await db.execute(
                    select(DriveInviteToken).where(
                        DriveInviteToken.token == token,
                        DriveInviteToken.drive_id == drive_id,
                        DriveInviteToken.is_used == False,
                    )
                )
                invite = result.scalars().first()
                if not invite:
                    await manager.send_json({"type": "error", "data": "Invalid or expired invite link."}, session_id)
                    return
                if invite.expires_at:
                    # Make timezone-aware for comparison if naive
                    expires = invite.expires_at
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=timezone.utc)
                    if expires < datetime.now(timezone.utc):
                        await manager.send_json({"type": "error", "data": "This invite link has expired."}, session_id)
                        return

                candidate_email = invite.candidate_email
                candidate_name = (candidate_email or "").split("@")[0]
                invite.is_used = True
                db.add(invite)

                # Find or create shadow user
                user_result = await db.execute(select(User).where(User.email == candidate_email))
                user = user_result.scalars().first()
                if not user:
                    base = (candidate_email or "guest").split("@")[0]
                    username, n = base, 0
                    while (await db.execute(select(User).where(User.username == username))).scalars().first():
                        n += 1
                        username = f"{base}_{n}"
                    # Generate secure random password for guest users
                    import secrets
                    guest_password = secrets.token_urlsafe(16)
                    user = User(
                        email=candidate_email, username=username,
                        password_hash=security.get_password_hash(guest_password), user_type="student",
                        first_name="Guest", last_name="Candidate", is_active=True,
                    )
                    db.add(user)
                    await db.flush()

                candidate_id = user.id

                # Fetch drive
                drive_res = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
                drive = drive_res.scalars().first()
                if drive:
                    job_role = drive.job_role
                    drive_title = drive.title
                    resume_text = f"Applying for: {drive.job_role}. Required skills: {drive.skills_required or 'General'}"
                    hr_prof_res = await db.execute(select(HRProfile).where(HRProfile.id == drive.hr_id))
                    hr_profile = hr_prof_res.scalars().first()
                    if hr_profile:
                        hr_user_res = await db.execute(select(User).where(User.id == hr_profile.user_id))
                        hr_user = hr_user_res.scalars().first()
                        if hr_user:
                            hr_email, hr_name = hr_user.email, hr_user.first_name

                new_session = InterviewSession(
                    candidate_id=candidate_id, job_drive_id=drive_id,
                    session_type="actual", status="in_progress",
                    start_time=datetime.now(timezone.utc),
                )
                db.add(new_session)
                await db.commit()
                await db.refresh(new_session)
                db_session_id = new_session.id

            await manager.send_json({"type": "status", "data": f"Session verified for {candidate_email}."}, session_id)
            if candidate_email:
                asyncio.create_task(send_interview_started_email(candidate_email, candidate_name, job_role))

        elif auth_token:
            # ── Authenticated practice session — validate JWT (#4) ──
            user_id = _verify_ws_token(auth_token)
            if not user_id:
                await manager.send_json({"type": "error", "data": "Invalid authentication token."}, session_id)
                return

            async with async_session() as db:
                user_res = await db.execute(select(User).where(User.id == user_id))
                user = user_res.scalars().first()
                if not user:
                    await manager.send_json({"type": "error", "data": "User not found."}, session_id)
                    return

                candidate_name = user.first_name
                candidate_email = user.email

                # Fetch resume text from student profile (#3)
                profile_res = await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))
                profile = profile_res.scalars().first()
                if profile and profile.resume_text:
                    resume_text = profile.resume_text
                    job_role = f"Software Engineer (Skills: {profile.skills or 'General'})"

                new_session = InterviewSession(
                    candidate_id=user_id, session_type="practice",
                    status="in_progress", start_time=datetime.now(timezone.utc),
                )
                db.add(new_session)
                await db.commit()
                await db.refresh(new_session)
                db_session_id = new_session.id

            await manager.send_json({"type": "status", "data": f"Practice round ready, {candidate_name}."}, session_id)

        # ── 2. Build initial state ────────────────────────────────────────
        initial_state: InterviewState = {
            "messages": [],
            "resume_text": resume_text,
            "job_role": job_role,
            "current_question_index": 0,
            "max_questions": 12,
            "interview_complete": False,
            "current_phase": "warmup",
            "difficulty": "medium",
            "latest_score": 0.0,
            "metrics": {"accuracy": 0, "clarity": 0, "depth": 0, "communication": 0},
            "topic_scores": {},
            "topic_strengths": {},
            "interviewer_mode": "ai",
            "hr_instructions": None,
            "last_evaluation": None,
            "next_question": None,
            "code_snippet": None,
            "code_language": None,
            "is_coding_mode": False,
        }

        # ── 3. Start Interview ────────────────────────────────────────────
        try:
            current_values = None
            try:
                async with asyncio.timeout(60):  # 60 second timeout for initial question
                    async for event in interview_graph.astream(initial_state, config=config, stream_mode="values"):
                        if event.get("next_question"):
                            current_values = event
            except asyncio.TimeoutError:
                raise ValueError("AI engine timed out generating question")

            if not (current_values and current_values.get("next_question")):
                raise ValueError("AI engine failed to generate opening question")

            q = current_values["next_question"]
            await manager.send_json({
                "type": "question",
                "data": q,
                "job_role": job_role,
                "is_coding": current_values.get("is_coding_mode", False),
                "language": current_values.get("code_language", "python"),
            }, session_id)
        except Exception as e:
            logger.error(f"Interview start failed [{session_id}]: {e}")
            await manager.send_json({"type": "error", "data": f"Engine Error: {str(e)}"}, session_id)
            return

        # ── 4. Main Communication Loop ────────────────────────────────────
        all_questions = [current_values["next_question"]]  # track for #18

        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            user_answer = ""
            user_code = ""

            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") == "answer":
                        user_answer = payload.get("data", "")
                    elif payload.get("type") == "code":
                        user_code = payload.get("data", "")
                except (json.JSONDecodeError, ValueError) as e:
                    await manager.send_json({"type": "error", "data": "Invalid message format. Send valid JSON."}, session_id)
                    logger.warning(f"Invalid JSON from session {session_id}: {e}")
                    continue

            elif "bytes" in message:
                await manager.send_json({"type": "status", "data": "Voice Engine: Transcribing..."}, session_id)
                user_answer = await voice_service.transcribe_audio(message["bytes"])
                if not user_answer:
                    await manager.send_json({"type": "error", "data": "Could not understand audio. Please try again."}, session_id)
                    continue
                await manager.send_json({"type": "status", "data": f'Understood: "{user_answer}"'}, session_id)

            if user_answer or user_code:
                try:
                    update = (
                        {"code_snippet": user_code, "messages": [{"role": "user", "content": "[Code Submitted]"}]}
                        if user_code
                        else {"messages": [{"role": "user", "content": user_answer}]}
                    )

                    # Execute code via Judge0 before AI evaluation
                    if user_code:
                        await manager.send_json({"type": "status", "data": "Judge0: Executing code..."}, session_id)
                        exec_result = await code_execution_service.execute(
                            source_code=user_code,
                            language=initial_state.get("code_language") or "python",
                        )
                        await manager.send_json({"type": "execution_result", "data": exec_result}, session_id)
                        # Enrich the code snippet with execution output for AI evaluation
                        enriched_content = (
                            f"[Code Submitted]\n"
                            f"Status: {exec_result['status']}\n"
                            f"Output: {exec_result['stdout'][:500]}\n"
                            f"Errors: {exec_result['stderr'][:300]}"
                        )
                        update = {"code_snippet": user_code, "messages": [{"role": "user", "content": enriched_content}]}
                    await interview_graph.aupdate_state(config, update)

                    async for chunk in interview_graph.astream(None, config=config, stream_mode="updates"):
                        for node_name, output in chunk.items():
                            if node_name in ("evaluate_answer", "evaluate_code"):
                                await manager.send_json({"type": "status", "data": "AI: Evaluating response..."}, session_id)
                                if output.get("metrics"):
                                    await manager.send_json({"type": "metrics_update", "data": output["metrics"]}, session_id)
                            elif node_name == "generate_question" and output.get("next_question"):
                                q = output["next_question"]
                                all_questions.append(q)  # #18: track questions
                                await manager.send_json({
                                    "type": "question",
                                    "data": q,
                                    "is_coding": output.get("is_coding_mode", False),
                                    "language": output.get("code_language", "python"),
                                }, session_id)

                    final_state = await interview_graph.aget_state(config)
                    if final_state.values.get("interview_complete"):
                        await manager.send_json({"type": "status", "data": "Assessment complete. Generating report..."}, session_id)

                        final_history = final_state.values.get("messages", [])
                        report = await evaluation_service.generate_final_report(job_role, final_history)
                        report_dict = report.model_dump()

                        # Persist session (#5 duration, #18 questions)
                        if db_session_id:
                            end_time = datetime.now(timezone.utc)
                            duration_secs = int((end_time - session_start).total_seconds())
                            async with async_session() as db:
                                res = await db.execute(select(InterviewSession).where(InterviewSession.id == db_session_id))
                                rec = res.scalars().first()
                                if rec:
                                    rec.status = "completed"
                                    rec.end_time = end_time
                                    rec.duration = duration_secs
                                    rec.questions = all_questions          # native JSON
                                    rec.responses = final_history          # native JSON
                                    rec.ai_feedback = report_dict          # native JSON
                                    rec.overall_score = report.overall_score
                                    db.add(rec)
                                    await db.commit()

                        await manager.send_json({
                            "type": "complete",
                            "report": report_dict,
                            "session_id": db_session_id,
                        }, session_id)

                        if candidate_email:
                            asyncio.create_task(send_report_to_candidate(candidate_email, candidate_name or "Candidate", job_role, report_dict))
                        if hr_email:
                            asyncio.create_task(send_report_to_hr(hr_email, hr_name or "HR", candidate_email or "Guest", job_role, drive_title or job_role, report_dict, str(db_session_id)))
                        break

                except Exception as e:
                    logger.error(f"Processing error [{session_id}]: {e}")
                    traceback.print_exc()
                    await manager.send_json({"type": "error", "data": f"Processing Error: {str(e)}"}, session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket fatal error [{session_id}]: {e}")
        traceback.print_exc()
        await manager.send_json({"type": "error", "data": str(e)}, session_id)
        manager.disconnect(session_id)


# ── HR Live Instruction Injection (audit #14: requires HR auth) ──────────────
@router.post("/sessions/{session_id}/hr-instruction")
@limiter.limit("20/minute")
async def send_hr_instruction(
    request: Request,
    session_id: str,
    instruction: Dict[str, str],
    current_hr: User = Depends(deps.get_current_hr),  # #14: auth required
):
    config = {"configurable": {"thread_id": session_id}}
    await interview_graph.aupdate_state(config, {"hr_instructions": instruction.get("text", "")})
    return {"status": "ok", "message": "Instruction queued for next AI turn."}
