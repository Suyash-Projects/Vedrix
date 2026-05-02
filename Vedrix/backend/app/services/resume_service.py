import fitz  # PyMuPDF
from typing import Optional, List


class ResumeParser:
    """Service to handle resume text extraction and initial parsing."""

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extracts plain text from a PDF file using PyMuPDF (fitz)."""
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
