from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json

from app.services.interview_engine.graph import interview_graph
from app.services.interview_engine.state import InterviewState

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
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time adaptive interviews.
    Orchestrates the LangGraph engine state machine via bi-directional communication.
    """
    await manager.connect(websocket, session_id)
    
    # Thread configuration for LangGraph checkpointer
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # 1. Initialize the Interview State
        # In production, we would fetch role/resume from the database using session_id
        initial_state: InterviewState = {
            "messages": [],
            "resume_text": "Experienced Python developer with a background in machine learning and FastAPI.",
            "job_role": "Senior Backend Engineer",
            "current_question_index": 0,
            "max_questions": 12, # Increased as per vision
            "interview_complete": False,
            "current_phase": "warmup", # Start at warmup
            "difficulty": "medium",
            "latest_score": 0.0,
            "metrics": {"accuracy": 0, "clarity": 0, "depth": 0, "communication": 0},
            "topic_scores": {},
            "topic_strengths": {},
            "interviewer_mode": "ai", # Default to AI autonomous
            "hr_instructions": None,
            "last_evaluation": None,
            "next_question": None
        }

        # 2. Start Interview: Invoke graph to generate the first question
        # Execution will pause before 'evaluate_answer' due to interrupt_before
        state_snapshot = interview_graph.invoke(initial_state, config=config)
        
        # Send initial question to frontend
        if state_snapshot.get('next_question'):
            await manager.send_json({
                "type": "question",
                "data": state_snapshot['next_question']
            }, session_id)

        # 3. Main Communication Loop
        while True:
            # Wait for user answer
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("type") == "answer":
                user_answer = payload.get("data", "")
                
                # Update graph state with the candidate's answer
                interview_graph.update_state(
                    config, 
                    {"messages": [{"role": "user", "content": user_answer}]},
                    as_node="evaluate_answer" # Mock the message source
                )
                
                await manager.send_json({"type": "status", "data": "AI is evaluating your response..."}, session_id)
                
                # Resume graph execution: evaluate_answer -> update_memory -> generate_question
                # It will pause again before the NEXT 'evaluate_answer'
                updated_snapshot = interview_graph.invoke(None, config=config)
                
                if updated_snapshot.get('interview_complete'):
                    await manager.send_json({
                        "type": "complete",
                        "data": "Interview finished. Generating feedback..."
                    }, session_id)
                    break
                
                # Send the next generated question
                if updated_snapshot.get('next_question'):
                    await manager.send_json({
                        "type": "question",
                        "data": updated_snapshot['next_question']
                    }, session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"Session {session_id} disconnected.")
    except Exception as e:
        print(f"WebSocket Error in session {session_id}: {e}")
        await manager.send_json({"type": "error", "data": str(e)}, session_id)
        manager.disconnect(session_id)
