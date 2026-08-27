"""Job state machine — Spec Table 4."""

from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "RETRY", "TERMINAL_FAILURE"]


class Job(BaseModel):
    job_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    job_type: str = Field(min_length=1)
    status: JobStatus = "PENDING"
    attempt: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    worker_type: str | None = None


# Valid transitions per Spec 
VALID_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    "PENDING": {"RUNNING", "FAILED"},
    "RUNNING": {"SUCCEEDED", "FAILED", "RETRY"},
    "RETRY": {"RUNNING", "TERMINAL_FAILURE"},
    "FAILED": {"RETRY", "TERMINAL_FAILURE"},
    "SUCCEEDED": set(),
    "TERMINAL_FAILURE": set(),
}


def can_transition(from_status: JobStatus, to_status: JobStatus) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, set())
