"""Privacy and redaction helpers for iStore Solar."""

from __future__ import annotations

import json
import re
from typing import Any, Final


REDACTED: Final = "**REDACTED**"
MAX_RESPONSE_PREVIEW_LENGTH: Final = 240

SENSITIVE_KEYS: Final[tuple[str, ...]] = (
    "account",
    "address",
    "authorization",
    "cipher",
    "cookie",
    "customer",
    "device",
    "email",
    "id",
    "latitude",
    "longitude",
    "mdm",
    "name",
    "nmi",
    "owner",
    "password",
    "phone",
    "publickey",
    "public_key",
    "serial",
    "session",
    "sid",
    "sn",
    "token",
    "uri",
    "user",
)

SAFE_DIAGNOSTIC_KEYS: Final[tuple[str, ...]] = (
    "entry_password_configured",
    "entry_token_present",
    "password_configured",
    "token_present",
)

SENSITIVE_VALUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(?i)(authorization|cookie|password|token|sid)=([^&\s]+)"),
    re.compile(
        r"\b[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}\b"
    ),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b"),
)


def redact_sensitive_data(value: Any) -> Any:
    """Return a recursively redacted copy of diagnostic data."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in SAFE_DIAGNOSTIC_KEYS:
                redacted[key] = redact_sensitive_data(item)
            elif any(sensitive in lowered for sensitive in SENSITIVE_KEYS):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_sensitive_data(item)
        return redacted

    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)

    if isinstance(value, str):
        return sanitize_text(value)

    return value


def sanitize_content_type(content_type: str | None) -> str | None:
    """Return a safe response content type without parameters."""
    if content_type is None:
        return None
    media_type = content_type.split(";", 1)[0].strip().lower()
    return sanitize_text(media_type) if media_type else None


def sanitize_response_preview(text: str, content_type: str | None) -> str | None:
    """Return a short sanitized response preview when it is safe enough."""
    if not text:
        return None

    preview_value: Any = text
    if content_type is not None and "json" in content_type:
        try:
            preview_value = redact_sensitive_data(json.loads(text))
        except ValueError:
            preview_value = text

    if isinstance(preview_value, str):
        preview_text = preview_value
    else:
        preview_text = json.dumps(preview_value, sort_keys=True)
    preview = sanitize_text(preview_text)
    if not preview:
        return None
    return preview[:MAX_RESPONSE_PREVIEW_LENGTH]


def sanitize_text(value: str) -> str:
    """Remove token-looking and identifier-looking values from diagnostic text."""
    sanitized = " ".join(value.split())
    for pattern in SENSITIVE_VALUE_PATTERNS:
        sanitized = pattern.sub(REDACTED, sanitized)
    return sanitized
