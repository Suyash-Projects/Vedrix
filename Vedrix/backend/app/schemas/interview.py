from typing import Optional, List, Any, TypedDict
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class EmpathyMetrics(TypedDict):
    """
    Real-time sentiment and emotional intelligence metrics for a candidate response.

    Design: Sentiment_Agent (Section 6 of design.md)
    Requirements: 6.1, 6.2

    Fields:
        sentiment_score: Overall sentiment polarity (-1.0 negative to 1.0 positive)
        stress_level: Detected stress/anxiety level (0.0 calm to 1.0 highly stressed)
        hesitation_rating: Degree of hesitation/uncertainty (0.0 decisive to 1.0 very hesitant)
        confidence_level: Detected confidence in responses (0.0 unconfident to 1.0 very confident)
        analyzed_at: ISO 8601 timestamp of when the analysis was performed
    """
    sentiment_score: float    # -1.0 to 1.0
    stress_level: float       # 0.0 to 1.0
    hesitation_rating: float  # 0.0 to 1.0
    confidence_level: float   # 0.0 to 1.0
    analyzed_at: str          # ISO timestamp

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
