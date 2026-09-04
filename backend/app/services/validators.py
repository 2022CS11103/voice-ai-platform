from __future__ import annotations

import re
from typing import Optional

# Common disposable / fake domains — block for signup
_DISPOSABLE = {
    "mailinator.com",
    "guerrillamail.com",
    "tempmail.com",
    "temp-mail.org",
    "10minutemail.com",
    "yopmail.com",
    "trashmail.com",
    "fakeinbox.com",
    "sharklasers.com",
    "throwaway.email",
}


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_business_email(email: str) -> str:
    """Require a real-looking email; reject disposable domains."""
    from email_validator import EmailNotValidError, validate_email

    cleaned = normalize_email(email)
    try:
        result = validate_email(cleaned, check_deliverability=False)
        cleaned = result.normalized
    except EmailNotValidError as exc:
        raise ValueError(f"Invalid email address: {exc}") from exc

    domain = cleaned.split("@", 1)[-1]
    if domain in _DISPOSABLE:
        raise ValueError("Disposable email addresses are not allowed. Use a real email.")
    if "." not in domain:
        raise ValueError("Email domain looks invalid.")
    return cleaned


def normalize_phone(raw: str) -> str:
    """Normalize to E.164-ish unique form."""
    cleaned = re.sub(r"[^\d+]", "", (raw or "").strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned.startswith("+"):
        if len(cleaned) == 10 and cleaned[0] in "6789":
            cleaned = "+91" + cleaned
        elif cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = "+" + cleaned
        elif cleaned.startswith("1") and len(cleaned) == 11:
            cleaned = "+" + cleaned
        else:
            cleaned = "+" + cleaned if cleaned else ""
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Enter a valid phone number with country code, e.g. +918318762518")
    return "+" + digits if not cleaned.startswith("+") else cleaned


def phones_equal(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    try:
        return normalize_phone(a) == normalize_phone(b)
    except ValueError:
        return False
