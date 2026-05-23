"""
Database encryption utilities for sensitive data protection.
Uses field-level encryption for PII and sensitive information.
"""
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Any
import json
import logging
from sqlalchemy import TypeDecorator, Text

logger = logging.getLogger(__name__)


class FieldEncryption:
    """
    Encrypt sensitive fields before database storage.
    Uses Fernet (symmetric encryption) with key derived from SECRET_KEY.
    """

    _fernet: Optional[Fernet] = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance (singleton)."""
        if cls._fernet is None:
            from app.core.config import settings

            # Derive key from SECRET_KEY using PBKDF2
            key = cls._derive_key(settings.SECRET_KEY)
            cls._fernet = Fernet(key)

        return cls._fernet

    @staticmethod
    def _derive_key(secret_key: str) -> bytes:
        """Derive encryption key from secret using PBKDF2."""
        salt = b'vedrix_field_encryption_salt'  # Fixed salt for consistency

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return key

    @classmethod
    def encrypt(cls, value: str) -> str:
        """Encrypt a string value."""
        if not value:
            return value

        try:
            fernet = cls._get_fernet()
            encrypted = fernet.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    @classmethod
    def decrypt(cls, encrypted_value: str) -> str:
        """Decrypt an encrypted string value."""
        if not encrypted_value:
            return encrypted_value

        try:
            fernet = cls._get_fernet()
            decrypted = fernet.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    @classmethod
    def hash_for_comparison(cls, value: str) -> str:
        """
        Create a hash for comparison (for data that needs to be
        compared but not stored in plaintext).
        """
        return hashlib.sha256(value.encode()).hexdigest()


class SensitiveDataMasker:
    """Mask sensitive data for logging and display."""

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address (e.g., user***@domain.com)."""
        if not email or '@' not in email:
            return "***"

        local, domain = email.split('@', 1)
        masked_local = local[:2] + "***" if len(local) > 2 else "***"
        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number (e.g., ***-***-1234)."""
        if not phone:
            return "***"

        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) < 4:
            return "***-***-****"

        return f"***-***-{digits[-4:]}"

    @staticmethod
    def mask_sensitive_dict(data: dict, fields: list[str]) -> dict:
        """Mask specified fields in a dictionary."""
        masked = data.copy()
        for field in fields:
            if field in masked:
                value = masked[field]
                if '@' in str(value):
                    masked[field] = SensitiveDataMasker.mask_email(str(value))
                elif value and len(str(value)) > 4:
                    masked[field] = "***" + str(value)[-4:]
                else:
                    masked[field] = "***"
        return masked


# ── Encryption Middleware for Models ───────────────────────────────────────────
class EncryptedField:
    """
    Descriptor for automatically encrypting/decrypting model fields.
    Usage in model:
        password = EncryptedField('password')
    """

    def __init__(self, field_name: str):
        self.field_name = field_name
        self.attr_name = f"_encrypted_{field_name}"

    def __get__(self, instance, owner):
        if instance is None:
            return self

        encrypted_value = getattr(instance, self.attr_name, None)
        if encrypted_value:
            try:
                return FieldEncryption.decrypt(encrypted_value)
            except Exception:
                return encrypted_value
        return None

    def __set__(self, instance, value):
        if value:
            encrypted = FieldEncryption.encrypt(value)
            setattr(instance, self.attr_name, encrypted)
        else:
            setattr(instance, self.attr_name, value)


# ── Database Backup Encryption ───────────────────────────────────────────────
class BackupEncryption:
    """Encrypt database backups for secure storage."""

    @staticmethod
    def encrypt_backup(data: bytes, password: str) -> bytes:
        """Encrypt backup data with password."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        # Generate random salt and IV
        salt = os.urandom(16)
        iv = os.urandom(16)

        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())

        # Encrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # Pad data to block size
        padding = 16 - (len(data) % 16)
        padded_data = data + bytes([padding] * padding)

        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Return salt + IV + encrypted data
        return salt + iv + encrypted

    @staticmethod
    def decrypt_backup(encrypted_data: bytes, password: str) -> bytes:
        """Decrypt backup data with password."""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        # Extract salt, IV, and encrypted data
        salt = encrypted_data[:16]
        iv = encrypted_data[16:32]
        encrypted = encrypted_data[32:]

        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())

        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        decrypted = decryptor.update(encrypted) + decryptor.finalize()

        # Remove padding
        padding = decrypted[-1]
        return decrypted[:-padding]


class EncryptedJSON(TypeDecorator):
    """
    Transparently encrypt/decrypt JSON data for database storage.
    Ensures sensitive interview transcripts and feedback are encrypted at rest.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        try:
            json_str = json.dumps(value)
            return FieldEncryption.encrypt(json_str)
        except Exception as e:
            logger.error(f"Failed to encrypt JSON for storage: {e}")
            return None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        
        # Try to decrypt
        try:
            decrypted_str = FieldEncryption.decrypt(value)
            return json.loads(decrypted_str)
        except Exception:
            # Fallback: maybe it's already plaintext JSON (for migration/dev)
            try:
                return json.loads(value)
            except Exception:
                logger.error("Failed to decrypt or parse JSON from database")
                return value


class EncryptedString(TypeDecorator):
    """
    Transparently encrypt/decrypt string data for database storage.
    Useful for PII like resume text, phone numbers, or addresses.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        try:
            return FieldEncryption.encrypt(str(value))
        except Exception as e:
            logger.error(f"Failed to encrypt string for storage: {e}")
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        
        # Try to decrypt
        try:
            return FieldEncryption.decrypt(value)
        except Exception:
            # Fallback: maybe it's already plaintext (for migration/dev)
            return value
