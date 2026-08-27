"""Per-type technical metadata — Spec §17 Table 5."""

from typing import Literal

from pydantic import BaseModel, Field

AssetType = Literal["video", "image", "audio", "document", "other"]


class VideoTechnicalMetadata(BaseModel):
    asset_id: str
    asset_type: Literal["video"] = "video"
    duration_seconds: float | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    fps: float | None = Field(default=None, gt=0)
    codec: str | None = None
    bitrate: int | None = Field(default=None, gt=0)
    audio_tracks: int | None = Field(default=None, ge=0)


class ImageTechnicalMetadata(BaseModel):
    asset_id: str
    asset_type: Literal["image"] = "image"
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    color_space: str | None = None
    format: str | None = None
    orientation: str | None = None


class AudioTechnicalMetadata(BaseModel):
    asset_id: str
    asset_type: Literal["audio"] = "audio"
    duration_seconds: float | None = Field(default=None, ge=0)
    codec: str | None = None
    sample_rate: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, gt=0)
    bitrate: int | None = Field(default=None, gt=0)


class DocumentTechnicalMetadata(BaseModel):
    asset_id: str
    asset_type: Literal["document"] = "document"
    page_count: int | None = Field(default=None, gt=0)
    file_format: str | None = None
    author: str | None = None
    creation_date: str | None = None
    size_bytes: int | None = Field(default=None, gt=0)
