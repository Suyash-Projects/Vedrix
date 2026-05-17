"""
Bulk import service for CSV candidate import with validation.

Supports importing candidates from CSV files with the following columns:
- email (required)
- first_name (required)
- last_name (required)
- username (optional, auto-generated if not provided)
- phone (optional)
- company (optional)
- role (optional, defaults to 'student')

Returns validation results and import statistics.
"""
import csv
import io
import re
import secrets
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, field_validator

logger = logging.getLogger(__name__)

# Required fields for candidate import
REQUIRED_FIELDS = ["email", "first_name", "last_name"]

# Optional fields with defaults
OPTIONAL_FIELDS = {
    "username": "",
    "phone": "",
    "company": "",
    "role": "student",
}

# Valid roles
VALID_ROLES = {"student", "hr", "admin"}

# Email regex pattern
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class CandidateImportRow(BaseModel):
    """Schema for a single candidate import row."""
    email: str
    first_name: str
    last_name: str
    username: Optional[str] = None
    phone: Optional[str] = ""
    company: Optional[str] = ""
    role: Optional[str] = "student"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_PATTERN.match(v):
            raise ValueError(f"Invalid email format: {v}")
        return v.lower()

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role: {v}. Must be one of {VALID_ROLES}")
        return v


class ImportResult(BaseModel):
    """Result of a bulk import operation."""
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    errors: List[Dict[str, Any]]
    candidates: List[Dict[str, Any]]


class BulkImportService:
    """Service for bulk importing candidates from CSV files."""

    @staticmethod
    def parse_csv(csv_content: str) -> List[Dict[str, str]]:
        """Parse CSV content and return list of row dictionaries."""
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            rows = []
            for row in reader:
                # Strip whitespace from keys and values
                cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                rows.append(cleaned_row)
            return rows
        except csv.Error as e:
            raise ValueError(f"Invalid CSV format: {str(e)}")

    @staticmethod
    def validate_row(row: Dict[str, str], row_number: int) -> tuple[bool, List[str]]:
        """Validate a single row and return (is_valid, errors)."""
        errors = []

        # Check required fields
        for field in REQUIRED_FIELDS:
            if not row.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate email format if present
        email = row.get("email", "")
        if email and not EMAIL_PATTERN.match(email):
            errors.append(f"Invalid email format: {email}")

        # Validate role if present
        role = row.get("role", "student")
        if role not in VALID_ROLES:
            errors.append(f"Invalid role: {role}. Must be one of {VALID_ROLES}")

        # Validate name fields
        for field in ["first_name", "last_name"]:
            value = row.get(field, "")
            if value and not value.strip():
                errors.append(f"{field} cannot be empty")

        return (len(errors) == 0, errors)

    @staticmethod
    def generate_username(first_name: str, last_name: str) -> str:
        """Generate a unique username from name."""
        base = f"{first_name.lower()}.{last_name.lower()}"
        # Remove special characters
        base = re.sub(r"[^a-z0-9.]", "", base)
        # Add random suffix to ensure uniqueness
        suffix = secrets.token_hex(2)
        return f"{base}_{suffix}"

    @staticmethod
    def generate_password() -> str:
        """Generate a secure random password."""
        return secrets.token_urlsafe(10)

    @staticmethod
    def process_import(
        csv_content: str,
        existing_emails: set,
        dry_run: bool = True,
    ) -> ImportResult:
        """
        Process a CSV import and return validation results.

        Args:
            csv_content: Raw CSV string content
            existing_emails: Set of existing email addresses to check for duplicates
            dry_run: If True, only validate without creating candidates

        Returns:
            ImportResult with validation statistics and errors
        """
        rows = BulkImportService.parse_csv(csv_content)

        result = ImportResult(
            total_rows=len(rows),
            valid_rows=0,
            invalid_rows=0,
            duplicate_rows=0,
            errors=[],
            candidates=[],
        )

        for idx, row in enumerate(rows, start=2):  # Start at 2 (row 1 is header)
            is_valid, validation_errors = BulkImportService.validate_row(row, idx)

            if not is_valid:
                result.invalid_rows += 1
                result.errors.append({
                    "row": idx,
                    "email": row.get("email", "N/A"),
                    "errors": validation_errors,
                })
                continue

            # Check for duplicates
            email = row.get("email", "").lower()
            if email in existing_emails:
                result.duplicate_rows += 1
                result.errors.append({
                    "row": idx,
                    "email": email,
                    "errors": ["Email already exists in the system"],
                })
                continue

            # Generate missing fields
            username = row.get("username") or BulkImportService.generate_username(
                row["first_name"], row["last_name"]
            )
            password = BulkImportService.generate_password()

            candidate = {
                "email": email,
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "username": username,
                "password": password,
                "phone": row.get("phone", ""),
                "company": row.get("company", ""),
                "role": row.get("role", "student"),
            }

            result.candidates.append(candidate)
            result.valid_rows += 1

        return result

    @staticmethod
    def get_csv_template() -> str:
        """Return a CSV template string for candidate import."""
        template = "email,first_name,last_name,username,phone,company,role\n"
        template += "john@example.com,John,Doe,john_doe,+1234567890,Acme Corp,student\n"
        template += "jane@example.com,Jane,Smith,jane_smith,+0987654321,Tech Inc,student\n"
        return template


# Singleton instance
bulk_import_service = BulkImportService()
