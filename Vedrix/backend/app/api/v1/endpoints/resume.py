import os
import uuid
import shutil
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.profile import StudentProfile
from app.services.resume_service import ResumeParser

router = APIRouter()

UPLOAD_DIR = "app/uploads/resumes"

@router.post("/student/resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """
    Endpoint: Upload Student Resume
    Process:
    1. Validates that the file is a PDF.
    2. Saves the file to a secure directory with a unique UUID.
    3. Calls the ResumeParser service to extract raw text from the PDF.
    4. Updates the student's profile with the new file reference and extracted text.
    
    This text is critical context for the adaptive AI interviewer.
    """
    if current_user.user_type != 'student':
        raise HTTPException(status_code=400, detail="Only students can upload resumes")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Save file with unique name
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract text using service
        extracted_text = await ResumeParser.extract_text(file_path)
        
        if not extracted_text:
            raise HTTPException(status_code=500, detail="Failed to extract text from resume")

        # Update Student Profile
        result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == current_user.id))
        db_profile = result.scalars().first()
        
        if not db_profile:
            db_profile = StudentProfile(user_id=current_user.id)
            db.add(db_profile)
        
        db_profile.resume_file = unique_filename
        db_profile.resume_text = extracted_text
        
        await db.commit()
        
        return {
            "status": "success", 
            "message": "Resume uploaded and processed",
            "filename": unique_filename
        }
        
    except Exception as e:
        # Cleanup file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))
