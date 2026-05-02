from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
import traceback

from sqlalchemy import select
from app.services.interview_engine.graph import interview_graph
from app.services.interview_engine.state import InterviewState
from app.services.voice_service import voice_service
from app.services.evaluation_service import evaluation_service
from app.services.email_service import (
    send_interview_started_email,
    send_report_to_candidate,
    send_report_to_hr,
)
from app.models.interview import InterviewSession, DriveInviteToken, JobDrive
from app.models.profile import HRProfile
from app.models.user import User
from app.db.session import async_session

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


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    drive_id: Optional[int] = None,
    token: Optional[str] = None,
    user_id: Optional[int] = None,
):
    await manager.connect(websocket, session_id)
    config = {"configurable": {"thread_id": session_id}}
    db_session_id: Optional[int] = None

    candidate_email: Optional[str] = None
    candidate_name: Optional[str] = None
    hr_email: Optional[str] = None
    hr_name: Optional[str] = None
    drive_title: Optional[str] = None

    try:
        # ── 1. Determine Context ──────────────────────────────────────────
        job_role = "Senior Backend Engineer"
        resume_text = "Experienced developer context."

        if drive_id and token:
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
                if invite.expires_at and invite.expires_at < datetime.utcnow():
                    await manager.send_json({"type": "error", "data": "This invite link has expired."}, session_id)
                    return

                candidate_email = invite.candidate_email
                candidate_name = (candidate_email or "").split("@")[0]
                invite.is_used = True
                db.add(invite)

                # Shadow User logic
                user_result = await db.execute(select(User).where(User.email == candidate_email))
                user = user_result.scalars().first()
                if not user:
                    base_username = (candidate_email or "guest").split("@")[0]
                    uname_count = 0
                    username = base_username
                    while True:
                        u_res = await db.execute(select(User).where(User.username == username))
                        if not u_res.scalars().first(): break
                        uname_count += 1
                        username = f"{base_username}_{uname_count}"
                    
                    user = User(
                        email=candidate_email,
                        username=username,
                        password_hash="guest_no_password",
                        user_type="student",
                        first_name="Guest",
                        last_name="Candidate",
                        is_active=True,
                    )
                    db.add(user)
                    await db.flush()

                candidate_id = user.id

                # Fetch drive metadata
                drive_result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
                drive = drive_result.scalars().first()
                if drive:
                    job_role = drive.job_role
                    drive_title = drive.title
                    resume_text = f"Applying for: {drive.job_role}. Skills: {drive.skills_required or 'General'}"
                    hr_prof_res = await db.execute(select(HRProfile).where(HRProfile.id == drive.hr_id))
                    hr_profile = hr_prof_res.scalars().first()
                    if hr_profile:
                        hr_user_res = await db.execute(select(User).where(User.id == hr_profile.user_id))
                        hr_user = hr_user_res.scalars().first()
                        if hr_user:
                            hr_email, hr_name = hr_user.email, hr_user.first_name

                # Create Session record
                new_session = InterviewSession(
                    candidate_id=candidate_id,
                    job_drive_id=drive_id,
                    session_type="actual",
                    status="in_progress",
                    start_time=datetime.utcnow(),
                )
                db.add(new_session)
                await db.commit()
                await db.refresh(new_session)
                db_session_id = new_session.id

            await manager.send_json({"type": "status", "data": f"Session verified for {candidate_email}."}, session_id)
            if candidate_email:
                asyncio.create_task(send_interview_started_email(candidate_email, candidate_name, job_role))

        elif user_id:
            # Authenticated Practice Session
            async with async_session() as db:
                user_res = await db.execute(select(User).where(User.id == user_id))
                user = user_res.scalars().first()
                if user:
                    new_session = InterviewSession(
                        candidate_id=user.id,
                        session_type="practice",
                        status="in_progress",
                        start_time=datetime.utcnow(),
                    )
                    db.add(new_session)
                    await db.commit()
                    await db.refresh(new_session)
                    db_session_id = new_session.id
                    await manager.send_json({"type": "status", "data": f"Practice round ready, {user.first_name}."}, session_id)

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
            async for event in interview_graph.astream(initial_state, config=config, stream_mode="values"):
                if event.get("next_question"):
                    current_values = event

            if current_values and current_values.get("next_question"):
                q = current_values["next_question"]
                audio_b64 = await voice_service.speak_text(q['question'])
                await manager.send_json({
                    "type": "question",
                    "data": q,
                    "audio": audio_b64,
                    "job_role": job_role,
                    "is_coding": current_values.get('is_coding_mode', False),
                    "language": current_values.get('code_language', 'python')
                }, session_id)
            else:
                raise ValueError("AI engine failed to initiate")
        except Exception as e:
            await manager.send_json({"type": "error", "data": f"Engine Error: {str(e)}"}, session_id)
            return

        # ── 4. Main Communication Loop ────────────────────────────────────
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
                except json.JSONDecodeError: continue

            elif "bytes" in message:
                audio_data = message["bytes"]
                await manager.send_json({"type": "status", "data": "Voice Engine: Transcribing..."}, session_id)
                user_answer = await voice_service.transcribe_audio(audio_data)
                if not user_answer:
                    await manager.send_json({"type": "error", "data": "Could not understand audio."}, session_id)
                    continue
                await manager.send_json({"type": "status", "data": f'Voice Engine: "{user_answer}"'}, session_id)

            if user_answer or user_code:
                try:
                    update_data = {}
                    if user_code:
                        update_data = {"code_snippet": user_code, "messages": [{"role": "user", "content": "[Code Submitted]"}]}
                    else:
                        update_data = {"messages": [{"role": "user", "content": user_answer}]}
                    
                    await interview_graph.aupdate_state(config, update_data)

                    async for chunk in interview_graph.astream(None, config=config, stream_mode="updates"):
                        for node_name, output in chunk.items():
                            if node_name == "evaluate_answer" or node_name == "evaluate_code":
                                await manager.send_json({"type": "status", "data": "AI: Evaluating response..."}, session_id)
                                if output.get("metrics"):
                                    await manager.send_json({"type": "metrics_update", "data": output["metrics"]}, session_id)
                            elif node_name == "generate_question":
                                if output.get("next_question"):
                                    q = output["next_question"]
                                    audio_b64 = await voice_service.speak_text(q['question'])
                                    await manager.send_json({
                                        "type": "question",
                                        "data": q,
                                        "audio": audio_b64,
                                        "is_coding": output.get("is_coding_mode", False),
                                        "language": output.get("code_language", "python")
                                    }, session_id)

                    final_state = await interview_graph.aget_state(config)
                    if final_state.values.get("interview_complete"):
                        await manager.send_json({"type": "status", "data": "Assessment complete. Wrapping up..."}, session_id)
                        report = await evaluation_service.generate_final_report(job_role, final_state.values.get("messages", []))
                        report_dict = report.model_dump()

                        if db_session_id:
                            async with async_session() as db:
                                res = await db.execute(select(InterviewSession).where(InterviewSession.id == db_session_id))
                                session_record = res.scalars().first()
                                if session_record:
                                    session_record.status = "completed"
                                    session_record.end_time = datetime.utcnow()
                                    session_record.responses = json.dumps(final_state.values.get("messages", []))
                                    session_record.ai_feedback = json.dumps(report_dict)
                                    session_record.overall_score = report.overall_score
                                    db.add(session_record)
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
                    traceback.print_exc()
                    await manager.send_json({"type": "error", "data": f"Flow Error: {str(e)}"}, session_id)

    except WebSocketDisconnect: manager.disconnect(session_id)
    except Exception as e:
        traceback.print_exc()
        await manager.send_json({"type": "error", "data": str(e)}, session_id)
        manager.disconnect(session_id)
