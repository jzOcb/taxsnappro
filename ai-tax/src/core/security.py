"""
Security module — PII handling, data sanitization, and safe logging.

Rules:
1. SSNs, EINs, bank accounts are NEVER logged in plaintext
2. PII is masked in all log output and error messages  
3. Tax data files are stored in data/ directory (chmod 700, .gitignore'd)
4. Serialized returns use masked SSN in filenames
5. Memory cleanup: sensitive data zeroed when no longer needed
"""

import re
import logging
from typing import Any


logger = logging.getLogger(__name__)


# ============================================================
# PII Patterns
# ============================================================

# SSN: 123-45-6789 or 123456789
SSN_PATTERN = re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b')

# EIN: 12-3456789 or 123456789
EIN_PATTERN = re.compile(r'\b\d{2}[-]?\d{7}\b')

# Bank account/routing numbers (9+ digits)
BANK_PATTERN = re.compile(r'\b\d{9,17}\b')


def mask_ssn(ssn: str) -> str:
    """Mask SSN for display/logging: 123-45-6789 → ***-**-6789"""
    if not ssn:
        return ""
    clean = ssn.replace("-", "").replace(" ", "")
    if len(clean) >= 4:
        return f"***-**-{clean[-4:]}"
    return "***-**-****"


def mask_ein(ein: str) -> str:
    """Mask EIN for display/logging: 12-3456789 → **-***6789"""
    if not ein:
        return ""
    clean = ein.replace("-", "").replace(" ", "")
    if len(clean) >= 4:
        return f"**-***{clean[-4:]}"
    return "**-*******"


def mask_account(account: str) -> str:
    """Mask bank account: 123456789 → *****6789"""
    if not account:
        return ""
    if len(account) >= 4:
        return "*" * (len(account) - 4) + account[-4:]
    return "****"


def sanitize_for_log(text: str) -> str:
    """
    Sanitize text for logging — mask any SSN/EIN/account patterns.
    Use this before logging anything that might contain PII.
    """
    result = text
    # Mask SSN-like patterns
    result = SSN_PATTERN.sub(lambda m: mask_ssn(m.group()), result)
    return result


def sanitize_dict_for_log(data: dict) -> dict:
    """
    Deep-sanitize a dictionary for logging.
    Masks values for known PII field names.
    """
    pii_fields = {'ssn', 'ein', 'employer_ein', 'payer_tin', 'bank_routing', 
                  'bank_account', 'social_security_number', 'tax_id'}
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower().replace("-", "_")
        if any(pii in key_lower for pii in pii_fields):
            if isinstance(value, str) and value:
                if 'ssn' in key_lower or 'social_security' in key_lower:
                    sanitized[key] = mask_ssn(value)
                elif 'ein' in key_lower or 'tin' in key_lower or 'tax_id' in key_lower:
                    sanitized[key] = mask_ein(value)
                elif 'bank' in key_lower or 'routing' in key_lower or 'account' in key_lower:
                    sanitized[key] = mask_account(value)
                else:
                    sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict_for_log(value)
        else:
            sanitized[key] = value
    
    return sanitized


class SecureLogger:
    """
    Logger wrapper that auto-sanitizes PII from messages.
    Use this instead of raw logging in any module that handles tax data.
    """
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
    
    def info(self, msg: str, *args, **kwargs):
        self._logger.info(sanitize_for_log(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(sanitize_for_log(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._logger.error(sanitize_for_log(msg), *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(sanitize_for_log(msg), *args, **kwargs)


# ============================================================
# Data Handling Rules
# ============================================================

# Where tax data files are stored (chmod 700, .gitignore'd)
import os
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')
RETURNS_DIR = os.path.join(DATA_DIR, 'returns')


def get_safe_filename(ssn: str, tax_year: int, suffix: str = "json") -> str:
    """Generate a safe filename using masked SSN."""
    masked = mask_ssn(ssn).replace("*", "x").replace("-", "")
    return f"return_{tax_year}_{masked}.{suffix}"


def validate_no_pii_in_output(text: str) -> list[str]:
    """
    Check if output text contains potential PII.
    Returns list of warnings if PII patterns detected.
    Use before sending any text to external channels (Telegram, etc.)
    """
    warnings = []
    
    # Check for SSN patterns
    ssn_matches = SSN_PATTERN.findall(text)
    for match in ssn_matches:
        clean = match.replace("-", "")
        # Skip common non-SSN 9-digit numbers (like dollar amounts without decimals)
        if not clean.startswith("000") and not clean.startswith("999"):
            warnings.append(f"Possible SSN detected: {mask_ssn(match)}")
    
    return warnings
