"""ASSET_CREATED event contract — v1.0 per Spec .1."""

from typing import Literal

from pydantic import BaseModel, Field

AssetType = Literal["video", "image", "audio", "document", "other"]


class AssetCreatedEvent(BaseModel):
    """Event emitted when a new asset lands in S3 raw."""

    event_type: Literal["ASSET_CREATED"] = "ASSET_CREATED"
    event_version: Literal["1.0"] = "1.0"
    asset_id: str = Field(min_length=1, description="Stable logical asset id")
    asset_type: AssetType
    bucket: str = Field(min_length=1)
    object_key: str = Field(min_length=1)
    object_version: str = Field(min_length=1)
    checksum: str = Field(min_length=1)
    created_at: str = Field(min_length=1, description="ISO8601 timestamp")
