from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    max_candidates: Optional[int] = Field(default=1, ge=1)

class SlotCreateBulk(BaseModel):
    slots: List[SlotCreate]

class SlotRead(BaseModel):
    id: int
    drive_id: int
    start_time: datetime
    end_time: datetime
    max_candidates: int
    booked_count: int
    
    class Config:
        from_attributes = True

class BookingCreate(BaseModel):
    slot_id: int

class BookingRead(BaseModel):
    id: int
    slot_id: int
    candidate_id: int
    session_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
