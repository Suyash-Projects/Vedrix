import fitz  # PyMuPDF
import asyncio
import logging
from typing import List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.services.interview_engine.providers import get_fast_llm

logger = logging.getLogger(__name__)


class SkillsSchema(BaseModel):
    skills: List[str] = Field(description="List of technical and soft skills extracted from the resume")


class ResumeParser:

    @staticmethod
    async def extract_text(file_path: str) -> str:
        """Extracts plain text from a PDF using PyMuPDF — runs in thread executor."""
        def _read():
            text = ""
            try:
                with fitz.open(file_path) as doc:
                    for page in doc:
                        text += page.get_text()
                return text.strip()
            except Exception as e:
                logger.error(f"PDF parse error: {e}")
                return ""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read)

    @staticmethod
    async def get_skills_summary(text: str) -> List[str]:
        """AI-based skill extraction — async to avoid blocking the event loop."""
        if not text:
            return []
        llm = get_fast_llm()
        parser = JsonOutputParser(pydantic_object=SkillsSchema)
        system_prompt = (
            "You are an expert recruiter. Extract a comprehensive list of technical and soft skills "
            "from the following resume text. Return a JSON object with a 'skills' key containing a list of strings."
        )
        try:
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Resume Text:\n{text[:4000]}")
            ])
            parsed = parser.parse(response.content)
            return parsed.get('skills', [])
        except Exception as e:
            logger.error(f"Skill extraction error: {e}")
            return []
