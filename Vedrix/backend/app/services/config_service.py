import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.config import PlatformConfig, ConfigChangeLog

logger = logging.getLogger(__name__)

# Predefined allowed models
AVAILABLE_MODELS = [
    "groq",
    "deepseek",
    "nvidia",
    "openrouter",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "deepseek-chat",
    "deepseek-coder",
    "deepseek-reasoner",
    "gpt-4o-mini",
    "gpt-4o",
    "claude-3-5-sonnet",
    "nvidia/nemotron-4-340b",
]

DEFAULT_CONFIGS = {
    "ai_provider": "groq",
    "rate_limit_per_minute": 60,
    "session_timeout_minutes": 30,
    "max_interview_duration_minutes": 90,
    "enable_email_notifications": True,
    "enable_audit_logging": True,
    "passing_score_threshold": 6.0,
    "max_questions_per_drive": 10,
    "proctor_tab_switch_threshold": 3,
    "proctor_paste_threshold": 100,
    "ai_model_interview": "llama3-70b-8192",
    "ai_model_evaluation": "deepseek-chat",
    "ai_model_coaching": "gpt-4o-mini",
}


class ConfigService:
    @staticmethod
    def validate_value(key: str, val: Any) -> Any:
        """
        Validates the configuration value based on the key.
        Raises HTTPException 400 if validation fails.
        """
        # AI Provider validation
        if key == "ai_provider":
            allowed_providers = ["groq", "deepseek", "nvidia", "openrouter"]
            if val not in allowed_providers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid AI provider. Must be one of {allowed_providers}"
                )

        # AI Model validations
        elif key in ["ai_model_interview", "ai_model_evaluation", "ai_model_coaching"]:
            if val not in AVAILABLE_MODELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid AI model '{val}'. Must be one of {AVAILABLE_MODELS}"
                )

        # Passing score threshold validation (0.0 - 10.0)
        elif key == "passing_score_threshold":
            try:
                f_val = float(val)
                if not (0.0 <= f_val <= 10.0):
                    raise ValueError()
                return f_val
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Passing score threshold must be a float between 0.0 and 10.0"
                )

        # Positive integer validations
        elif key in [
            "rate_limit_per_minute",
            "session_timeout_minutes",
            "max_interview_duration_minutes",
            "max_questions_per_drive",
            "proctor_tab_switch_threshold",
            "proctor_paste_threshold",
        ]:
            try:
                i_val = int(val)
                if i_val <= 0:
                    raise ValueError()
                return i_val
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{key} must be a positive integer"
                )

        # Boolean validations
        elif key in ["enable_email_notifications", "enable_audit_logging"]:
            if not isinstance(val, bool):
                if str(val).lower() in ["true", "1", "yes"]:
                    return True
                elif str(val).lower() in ["false", "0", "no"]:
                    return False
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{key} must be a boolean value"
                )
            return val

        return val

    @classmethod
    async def get_all(cls, db: AsyncSession) -> Dict[str, Any]:
        """
        Loads all configurations from the database and returns a combined dictionary.
        Falls back to defaults for any keys not found in the DB.
        """
        result = await db.execute(select(PlatformConfig))
        db_configs = result.scalars().all()
        configs_dict = {cfg.key: json.loads(cfg.value) for cfg in db_configs}

        # Merge with default config values
        merged = {}
        for k, v in DEFAULT_CONFIGS.items():
            merged[k] = configs_dict.get(k, v)

        return merged

    @classmethod
    async def update(
        cls, db: AsyncSession, key: str, value: Any, changed_by_user_id: int
    ) -> PlatformConfig:
        """
        Updates a configuration key after validation, and logs the change to ConfigChangeLog.
        """
        # Validate key exists in defaults
        if key not in DEFAULT_CONFIGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown configuration key '{key}'"
            )

        # Validate and coerce value
        validated_val = cls.validate_value(key, value)

        # Fetch existing setting
        stmt = select(PlatformConfig).where(PlatformConfig.key == key)
        result = await db.execute(stmt)
        config_record = result.scalars().first()

        old_val_str = None
        new_val_str = json.dumps(validated_val)

        if config_record:
            old_val_str = config_record.value
            config_record.value = new_val_str
            config_record.updated_at = datetime.now(timezone.utc)
            db.add(config_record)
        else:
            config_record = PlatformConfig(
                key=key,
                value=new_val_str,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(config_record)

        # Create history log
        log_entry = ConfigChangeLog(
            key=key,
            old_value=old_val_str,
            new_value=new_val_str,
            changed_by_user_id=changed_by_user_id,
            changed_at=datetime.now(timezone.utc)
        )
        db.add(log_entry)

        await db.commit()
        await db.refresh(config_record)
        return config_record

    @classmethod
    async def get_history(cls, db: AsyncSession) -> List[ConfigChangeLog]:
        """
        Returns the configuration change log history, sorted from most to least recent.
        """
        stmt = select(ConfigChangeLog).order_by(ConfigChangeLog.changed_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())
