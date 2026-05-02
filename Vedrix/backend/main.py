from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings

from app.db.session import init_db

app = FastAPI(
    title="Vedrix AI Interview System",
    description="Modern AI-powered interview platform",
    version="1.0.0",
)

@app.on_event("startup")
async def on_startup():
    await init_db()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Welcome to Vedrix API", "status": "online"}
