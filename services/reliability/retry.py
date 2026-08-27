"""Bounded exponential backoff — Spec §23, §37."""

from typing import Literal

FailureClass = Literal["transient", "permanent", "unknown"]

TRANSIENT_ERRORS = {"Timeout", "Throttling", "ServiceUnavailable", "ECSTaskFailed", "NetworkError"}
PERMANENT_ERRORS = {"CorruptAsset", "UnsupportedFormat", "InvalidChecksum", "ValidationError"}


def classify_failure(error_code: str | None) -> FailureClass:
    if not error_code:
        return "unknown"
    if (
        error_code in TRANSIENT_ERRORS
        or "timeout" in error_code.lower()
        or "throttl" in error_code.lower()
    ):
        return "transient"
    if (
        error_code in PERMANENT_ERRORS
        or "corrupt" in error_code.lower()
        or "unsupported" in error_code.lower()
    ):
        return "permanent"
    return "unknown"


def should_retry(failure_class: FailureClass, attempt: int, max_attempts: int = 3) -> bool:
    """Bounded retry: only transient, within budget."""
    if failure_class != "transient":
        return False
    return attempt < max_attempts


def backoff_delay(
    attempt: int, base_seconds: float = 2.0, backoff_rate: float = 2.0, max_seconds: float = 30.0
) -> float:
    """Exponential backoff: base * rate^attempt, capped at max."""
    delay = base_seconds * (backoff_rate**attempt)
    return min(delay, max_seconds)
