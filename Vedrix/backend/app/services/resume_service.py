import fitz  # PyMuPDF
from typing import Optional, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.services.interview_engine.providers import get_fast_llm


class SkillsSchema(BaseModel):
    skills: List[str] = Field(description="List of technical and soft skills extracted from the resume")


class ResumeParser:
    """
    Service: Resume Parser
    Utility for extracting structured and raw data from candidate resumes.
    Currently utilizes PyMuPDF (fitz) for text extraction.
    """

    @staticmethod
    async def extract_text(file_path: str) -> str:
        """
        Extracts plain text from a PDF file using PyMuPDF (fitz).
        Used to provide background context to the adaptive LLM interviewer.
        """
        import asyncio
        def _read():
            text = ""
            try:
                with fitz.open(file_path) as doc:
                    for page in doc:
                        text += page.get_text()
                return text.strip()
            except Exception as e:
                print(f"Error parsing PDF: {e}")
                return ""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read)

    @staticmethod
    def get_skills_summary(text: str) -> List[str]:
        """
        AI-based skill extraction from raw resume text.
        Uses Groq for fast extraction.
        """
        if not text:
            return []
            
        llm = get_fast_llm()
        parser = JsonOutputParser(pydantic_object=SkillsSchema)
        
        system_prompt = """You are an expert recruiter. 
        Extract a comprehensive list of technical and soft skills from the following resume text.
        Return the result as a JSON object with a 'skills' key containing a list of strings.
        """
        
        try:
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Resume Text:\n{text[:4000]}")
            ])
            parsed = parser.parse(response.content)
            return parsed.get('skills', [])
        except Exception as e:
            print(f"Error extracting skills: {e}")
            return []
