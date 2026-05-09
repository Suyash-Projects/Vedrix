from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ScenarioTemplateBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: str  # 'coding', 'system_design', 'behavioral'
    difficulty_level: int = 1
    estimated_time: int = 30
    scenarios: Optional[Any] = None

class ScenarioTemplateCreate(ScenarioTemplateBase):
    pass

class ScenarioTemplateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    difficulty_level: Optional[int] = None
    estimated_time: Optional[int] = None
    scenarios: Optional[Any] = None

class ScenarioTemplateRead(ScenarioTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
