"""Worker input/output contracts — Spec ."""

from typing import Literal

from pydantic import BaseModel, Field


class WorkerInput(BaseModel):
    asset_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    input_uri: str = Field(min_length=1)
    output_uri: str = Field(min_length=1)
    pipeline_version: str = Field(default="1.0", min_length=1)


class WorkerOutput(BaseModel):
    asset_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    status: Literal["SUCCEEDED", "FAILED"]
    output_uri: str = Field(min_length=1)
    duration_ms: int = Field(ge=0)
    error_code: str | None = None
    checksum: str | None = None
