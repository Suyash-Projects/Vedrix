from fastapi import APIRouter
from .endpoints import auth, users, profiles, resume, interview, admin, hr, student

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(resume.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(interview.router, prefix="/interview", tags=["interview"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(hr.router, prefix="/hr", tags=["hr"])
api_router.include_router(student.router, prefix="/student", tags=["student"])
