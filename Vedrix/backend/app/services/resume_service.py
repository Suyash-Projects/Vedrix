import fitz  # PyMuPDF
from typing import Optional, List


class ResumeParser:
    """
    Service: Resume Parser
    Utility for extracting structured and raw data from candidate resumes.
    Currently utilizes PyMuPDF (fitz) for text extraction.
    """

    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extracts plain text from a PDF file using PyMuPDF (fitz).
        Used to provide background context to the adaptive LLM interviewer.
        """
        text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text.strip()
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return ""

    @staticmethod
    def get_skills_summary(text: str) -> List[str]:
        """Placeholder for AI-based skill extraction.
        Will later call the NVIDIA/Groq model to structure skills.
        """
        return []
