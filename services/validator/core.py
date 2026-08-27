"""Pure validation logic — no AWS SDK, testable locally (Spec )."""

from typing import Literal

from pydantic import BaseModel

from data.schemas.events import AssetCreatedEvent


class ValidationResult(BaseModel):
    valid: bool
    reason: str | None = None
    action: Literal["proceed", "quarantine"]


ALLOWED_TYPES = {"video", "image", "audio", "document", "other"}


def validate_asset(evt: AssetCreatedEvent) -> ValidationResult:
    if not evt.object_key or not evt.object_key.strip():
        return ValidationResult(valid=False, reason="missing object_key", action="quarantine")
    if not evt.checksum or not evt.checksum.strip():
        return ValidationResult(valid=False, reason="missing checksum", action="quarantine")
    if evt.asset_type not in ALLOWED_TYPES:
        return ValidationResult(
            valid=False, reason=f"unsupported asset_type: {evt.asset_type}", action="quarantine"
        )
    if not evt.bucket or not evt.object_version:
        return ValidationResult(valid=False, reason="missing bucket/version", action="quarantine")
    return ValidationResult(valid=True, action="proceed")
