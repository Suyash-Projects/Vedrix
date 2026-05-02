from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import traceback

from app.services.interview_engine.graph import interview_graph
from app.services.interview_engine.state import InterviewState
from app.services.voice_service import voice_service

router = APIRouter()

class ConnectionManager:
    """Manages active WebSocket connections for interview sessions."""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_json(self, message: Dict[str, Any], session_id: str):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except RuntimeError:
                self.disconnect(session_id)
            except Exception as e:
                print(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time adaptive interviews.
    Orchestrates the LangGraph engine state machine via bi-directional communication.
    Supports both text (JSON) and audio (binary) messages.
    """
    await manager.connect(websocket, session_id)
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # 1. Initialize the Interview State
        initial_state: InterviewState = {
            "messages": [],
            "resume_text": "Experienced Python developer with a background in machine learning and FastAPI.",
            "job_role": "Senior Backend Engineer",
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
            "next_question": None
        }

        # 2. Start Interview: Stream the first question
        try:
            async for event in interview_graph.astream(initial_state, config=config, stream_mode="values"):
                if event.get('next_question'):
                    current_values = event
            
            if current_values and current_values.get('next_question'):
                await manager.send_json({
                    "type": "question",
                    "data": current_values['next_question']
                }, session_id)
            else:
                raise ValueError("AI engine failed to initiate")
        except Exception as e:
            await manager.send_json({"type": "error", "data": f"Engine Error: {str(e)}"}, session_id)
            return

        # 3. Main Communication Loop
        while True:
            # Wait for user input (either text or audio bytes)
            message = await websocket.receive()
            user_answer = ""

            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") == "answer":
                        user_answer = payload.get("data", "")
                except json.JSONDecodeError:
                    continue
            
            elif "bytes" in message:
                # Candidate sent audio data (Priority 4)
                audio_data = message["bytes"]
                await manager.send_json({"type": "status", "data": "Voice Engine: Transcribing audio..."}, session_id)
                user_answer = await voice_service.transcribe_audio(audio_data)
                
                if not user_answer:
                    await manager.send_json({"type": "error", "data": "Voice Engine: I didn't catch that. Please speak again."}, session_id)
                    continue
                
                await manager.send_json({"type": "status", "data": f"Voice Engine: Understood: \"{user_answer}\""}, session_id)

            if user_answer:
                try:
                    # Update graph state with the candidate's answer
                    await interview_graph.aupdate_state(
                        config, 
                        {"messages": [{"role": "user", "content": user_answer}]}
                    )
                    
                    # Stream the agentic response cycle
                    async for chunk in interview_graph.astream(None, config=config, stream_mode="updates"):
                        for node_name, output in chunk.items():
                            if node_name == "evaluate_answer":
                                await manager.send_json({"type": "status", "data": "Evaluator Agent: Scoring technical depth..."}, session_id)
                                if output.get('metrics'):
                                    await manager.send_json({"type": "metrics_update", "data": output['metrics']}, session_id)
                            
                            elif node_name == "update_memory":
                                await manager.send_json({"type": "status", "data": "Decision Agent: Adjusting difficulty..."}, session_id)
                            
                            elif node_name == "generate_question":
                                await manager.send_json({"type": "status", "data": "Interviewer Agent: Drafting next question..."}, session_id)
                                if output.get('next_question'):
                                    await manager.send_json({"type": "question", "data": output['next_question']}, session_id)

                    # Check for completion
                    final_state = await interview_graph.aget_state(config)
                    if final_state.values.get('interview_complete'):
                        await manager.send_json({"type": "complete", "data": "Assessment finalized."}, session_id)
                        break
                except Exception as e:
                    traceback.print_exc()
                    await manager.send_json({"type": "error", "data": f"Processing Error: {str(e)}"}, session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        traceback.print_exc()
        await manager.send_json({"type": "error", "data": str(e)}, session_id)
        manager.disconnect(session_id)
