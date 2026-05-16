import json
import logging
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from .interview_engine.model_router import get_report_llm

logger = logging.getLogger(__name__)


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

    def __init__(self):
        self.llm = get_report_llm()

    async def generate_final_report(
        self, job_role: str, history: List[Dict[str, str]]
    ) -> DetailedEvaluationSchema:
        transcript = "\n".join(
            f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
            for m in history
        )
        system_prompt = (
            f"You are a principal engineer and expert hiring manager reviewing an AI-led interview "
            f"for the role of {job_role}.\n\n"
            "Provide a deep, clinical analysis. Be objective.\n"
            "OUTPUT FORMAT: Return a valid JSON object matching the requested schema exactly."
        )
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Transcript:\n{transcript}\n\nGenerate the final evaluation report."),
            ])
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return DetailedEvaluationSchema(**json.loads(content))
        except Exception as e:
            logger.error(f"Final report generation failed: {e}")
            return DetailedEvaluationSchema(
                overall_score=5.0,
                hire_recommendation="Maybe",
                technical_accuracy=5.0,
                communication_clarity=5.0,
                depth_of_knowledge=5.0,
                strengths=["Completed the session"],
                weaknesses=["Evaluation engine failed — manual review required"],
                summary="AI evaluation failed. Manual review of transcript required.",
            )


evaluation_service = EvaluationService()
