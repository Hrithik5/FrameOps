"""Universal asset metadata — Spec ."""

from typing import Literal

from pydantic import BaseModel, Field

AssetType = Literal["video", "image", "audio", "document", "other"]
AssetStatus = Literal["INGESTED", "VALIDATED", "PROCESSING", "ENRICHED", "PUBLISHED", "FAILED"]


class UniversalAssetMetadata(BaseModel):
    asset_id: str = Field(min_length=1)
    asset_type: AssetType
    source: str = Field(default="upload")
    original_uri: str = Field(min_length=1)
    status: AssetStatus
    file_name: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    file_size_bytes: int = Field(gt=0)
    checksum: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    processed_at: str | None = None
    processing_duration_ms: int | None = Field(default=None, ge=0)
