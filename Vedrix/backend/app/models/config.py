from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

class PlatformConfig(SQLModel, table=True):
    __tablename__ = "platform_config"

    key: str = Field(primary_key=True, nullable=False, index=True)
    value: str = Field(nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConfigChangeLog(SQLModel, table=True):
    __tablename__ = "config_change_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(nullable=False, index=True)
    old_value: Optional[str] = Field(default=None, nullable=True)
    new_value: str = Field(nullable=False)
    changed_by_user_id: int = Field(foreign_key="user.id", nullable=False)
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
