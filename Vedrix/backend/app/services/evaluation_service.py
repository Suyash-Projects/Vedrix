import json
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from app.core.config import settings

class DetailedEvaluationSchema(BaseModel):
    overall_score: float = Field(description="Final overall score out of 10.0")
    hire_recommendation: str = Field(description="One of: 'Strong Hire', 'Hire', 'Maybe', 'No Hire'")
    technical_accuracy: float = Field(description="Score 0-10 for correctness of answers")
    communication_clarity: float = Field(description="Score 0-10 for clarity and confidence")
    depth_of_knowledge: float = Field(description="Score 0-10 for seniority and depth")
    strengths: List[str] = Field(description="Top 3 technical or behavioral strengths")
    weaknesses: List[str] = Field(description="Key areas for improvement")
    summary: str = Field(description="A concise executive summary for HR")

class EvaluationService:
    """Service for deep post-interview analysis using high-capacity LLMs."""
    
    def __init__(self):
        # Using DeepSeek via OpenRouter for deep reasoning
        self.llm = ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model="deepseek/deepseek-chat-v3.1:free",
            temperature=0.1
        )

    async def generate_final_report(self, job_role: str, history: List[Dict[str, str]]) -> DetailedEvaluationSchema:
        """
        Analyzes the full conversation transcript and returns a structured report.
        """
        transcript = ""
        for msg in history:
            role = "Interviewer" if msg['role'] == 'assistant' else "Candidate"
            transcript += f"{role}: {msg['content']}\n"

        system_prompt = f"""You are a principal engineer and expert hiring manager.
        You are reviewing the transcript of an AI-led interview for the role of {job_role}.
        
        TASK:
        Provide a deep, clinical analysis of the candidate's performance.
        Be extremely objective. If technical answers were vague, score 'Depth' low.
        If accuracy was high but communication poor, reflect that in 'Communication'.
        
        OUTPUT FORMAT:
        You must return a valid JSON object matching the requested schema.
        """
        
        human_prompt = f"Transcript:\n{transcript}\n\nGenerate the final evaluation report."
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            # Extract JSON from response content (handling potential markdown blocks)
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            return DetailedEvaluationSchema(**parsed)
            
        except Exception as e:
            print(f"Deep Evaluation Error: {e}")
            # Robust fallback
            return DetailedEvaluationSchema(
                overall_score=5.0,
                hire_recommendation="Maybe",
                technical_accuracy=5.0,
                communication_clarity=5.0,
                depth_of_knowledge=5.0,
                strengths=["Completed the session"],
                weaknesses=["Technical depth analysis failed"],
                summary="AI Evaluation failed to generate a deep report. Manual review of transcript required."
            )

evaluation_service = EvaluationService()
