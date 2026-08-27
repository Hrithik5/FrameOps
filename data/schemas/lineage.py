"""Asset lineage — Spec §18."""

from pydantic import BaseModel, Field


class LineageRecord(BaseModel):
    parent_asset_id: str = Field(min_length=1)
    child_asset_id: str = Field(min_length=1)
    derivative_type: str = Field(min_length=1)
    pipeline_version: str = Field(default="1.0")
    created_at: str = Field(min_length=1)
    job_id: str | None = None


class ProcessingMetadata(BaseModel):
    asset_id: str
    pipeline_version: str = "1.0"
    jobs: list[dict[str, str]] = Field(default_factory=list)
