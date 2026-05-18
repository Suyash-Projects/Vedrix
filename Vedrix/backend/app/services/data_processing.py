"""
Data processing records service for GDPR compliance.
Logs what data is processed, why, and when.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Data processing registry
PROCESSING_RECORDS: Dict[str, Dict[str, Any]] = {
    "interview_evaluation": {
        "purpose": "Conduct AI-powered interview evaluations",
        "data_types": ["user_responses", "ai_feedback", "scores"],
        "legal_basis": "legitimate_interest",
        "retention_days": 365,
        "description": "User interview responses are processed by AI to generate evaluation scores and feedback.",
    },
    "analytics": {
        "purpose": "Generate analytics and insights",
        "data_types": ["interview_scores", "skill_matrix", "demographics"],
        "legal_basis": "consent",
        "retention_days": 730,
        "description": "Aggregated interview data is used to generate analytics and skill gap reports.",
    },
    "email_notifications": {
        "purpose": "Send interview invitations and credentials",
        "data_types": ["email", "name", "interview_details"],
        "legal_basis": "contract",
        "retention_days": 90,
        "description": "User email addresses are used to send interview invitations and account credentials.",
    },
    "certificate_generation": {
        "purpose": "Generate completion certificates",
        "data_types": ["name", "score", "interview_details"],
        "legal_basis": "legitimate_interest",
        "retention_days": 365,
        "description": "User names and scores are used to generate verifiable completion certificates.",
    },
    "ai_model_training": {
        "purpose": "Improve AI interview quality",
        "data_types": ["anonymized_responses", "scores"],
        "legal_basis": "consent",
        "retention_days": 180,
        "description": "Anonymized interview data may be used to improve AI question generation and evaluation.",
    },
}


def record_data_processing(
    processing_type: str,
    user_id: int,
    data_processed: Dict[str, Any],
    consent_given: bool = True,
) -> Dict[str, Any]:
    """
    Record a data processing event for GDPR compliance.

    Args:
        processing_type: Type of processing (must be in PROCESSING_RECORDS)
        user_id: ID of the user whose data is being processed
        data_processed: Description of what data was processed
        consent_given: Whether consent was given for this processing

    Returns:
        Processing record dictionary
    """
    if processing_type not in PROCESSING_RECORDS:
        logger.warning(f"Unknown processing type: {processing_type}")
        return {}

    record = PROCESSING_RECORDS[processing_type]

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_type": processing_type,
        "user_id": user_id,
        "purpose": record["purpose"],
        "legal_basis": record["legal_basis"],
        "data_types": record["data_types"],
        "consent_given": consent_given,
        "data_processed": data_processed,
    }

    logger.info(f"Data processing recorded: {processing_type} for user {user_id}")
    return log_entry


def get_processing_record(processing_type: str) -> Optional[Dict[str, Any]]:
    """Get a processing record by type."""
    return PROCESSING_RECORDS.get(processing_type)


def get_all_processing_records() -> Dict[str, Dict[str, Any]]:
    """Get all processing records."""
    return PROCESSING_RECORDS
