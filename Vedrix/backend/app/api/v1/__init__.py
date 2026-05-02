from fastapi import APIRouter
from .endpoints import auth, users, profiles, resume, interview

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(resume.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(interview.router, prefix="/interview", tags=["interview"])
