"""
Database security utilities.
Provides SQL injection prevention and input validation.
"""
import re
import logging
from typing import Any, Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SQLInjectionGuard:
    """Protection against SQL injection attacks."""

    # Dangerous SQL patterns
    DANGEROUS_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bdrop\b.*\bdatabase\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(\bsp_executesql\b)",
        r"(--\s*$)",
        r"(/\*.*\*/)",
        r"(\bor\b.*=.*)",
        r"(\band\b.*=.*)",
    ]

    COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]

    @classmethod
    def contains_dangerous_sql(cls, value: str) -> bool:
        """Check if string contains potentially dangerous SQL patterns."""
        if not isinstance(value, str):
            return False

        for pattern in cls.COMPILED_PATTERNS:
            if pattern.search(value):
                logger.warning(f"Potential SQL injection detected: {value[:50]}...")
                return True
        return False

    @classmethod
    def sanitize_input(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize user input by removing dangerous characters."""
        if not isinstance(value, str):
            return str(value)

        # Trim to max length
        value = value[:max_length]

        # Remove null bytes
        value = value.replace('\x00', '')

        # Remove common injection patterns
        value = re.sub(r"['\";].*", "", value)

        return value.strip()


class InputValidator:
    """Validate and sanitize user inputs."""

    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    USERNAME_PATTERN = re.compile(
        r'^[a-zA-Z0-9_-]{3,30}$'
    )

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        return bool(InputValidator.EMAIL_PATTERN.match(email))

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format (3-30 chars, alphanumeric + _-)."""
        return bool(InputValidator.USERNAME_PATTERN.match(username))

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """
        Validate password strength.
        Returns (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        if len(password) > 128:
            return False, "Password too long (max 128 characters)"

        # Check for mixed case
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase, lowercase, and digit"

        return True, ""

    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """Sanitize search query to prevent injection."""
        # Remove SQL wildcards that could be used for injection
        query = re.sub(r'[%_]', '', query)
        # Trim and limit length
        return query.strip()[:200]

    @staticmethod
    def validate_id(id_value: Any) -> Optional[int]:
        """Validate that ID is a positive integer."""
        try:
            id_int = int(id_value)
            if id_int > 0:
                return id_int
        except (ValueError, TypeError):
            pass
        return None


# ── Audit Logging ───────────────────────────────────────────────────────────────
class DatabaseAuditLogger:
    """Log sensitive database operations for security auditing."""

    @staticmethod
    async def log_query(
        session: AsyncSession,
        operation: str,
        table: str,
        record_id: Optional[int] = None,
        user_id: Optional[int] = None,
        details: Optional[dict] = None
    ) -> None:
        """
        Log a database operation for audit trail.
        In production, this would write to an audit table.
        """
        audit_entry = {
            "operation": operation,
            "table": table,
            "record_id": record_id,
            "user_id": user_id,
            "details": details,
        }

        # Log to standard logger (in production, use separate audit logging)
        logger.info(f"AUDIT: {audit_entry}")

    @staticmethod
    async def log_authentication(
        session: AsyncSession,
        user_id: int,
        success: bool,
        ip_address: Optional[str] = None
    ) -> None:
        """Log authentication attempts."""
        logger.info(
            f"AUTH: user_id={user_id} success={success} ip={ip_address}"
        )

    @staticmethod
    async def log_data_access(
        session: AsyncSession,
        user_id: int,
        resource: str,
        action: str
    ) -> None:
        """Log data access patterns."""
        logger.debug(
            f"DATA_ACCESS: user_id={user_id} resource={resource} action={action}"
        )