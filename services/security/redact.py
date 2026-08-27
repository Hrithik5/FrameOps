"""Secret redaction — Spec §26 bullet 3."""
# mypy: disable-error-code="type-arg,assignment,arg-type,unused-ignore"

import re
from typing import Any

SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "aws_secret_access_key", "checksum"}
REDACTED = "***REDACTED***"

# Regex for AWS keys, secrets etc.
AWS_ACCESS_KEY_RE = re.compile(r"AKIA[0-9A-Z]{16}")
SECRET_RE = re.compile(r"(?i)(password|secret|token)\s*[:=\s]\s*\S+")


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-redef]
    from typing import Any as _Any

    out: dict[str, _Any] = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_KEYS:
            out[k] = REDACTED
        elif isinstance(v, str) and AWS_ACCESS_KEY_RE.search(v):
            out[k] = AWS_ACCESS_KEY_RE.sub(REDACTED, v)
        elif isinstance(v, dict):
            out[k] = redact_dict(v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def redact_string(s: str) -> str:
    s = AWS_ACCESS_KEY_RE.sub(REDACTED, s)
    s = SECRET_RE.sub(lambda m: m.group(0).split(m.group(1))[0] + m.group(1) + "=***", s)
    return s
