"""Universal + technical metadata builder — writes canonical records."""

import datetime
from typing import Any

from data.schemas.asset import UniversalAssetMetadata
from data.schemas.technical import (
    AudioTechnicalMetadata,
    DocumentTechnicalMetadata,
    ImageTechnicalMetadata,
    VideoTechnicalMetadata,
)


def build_universal(
    asset_id: str,
    asset_type: str,
    original_uri: str,
    file_name: str,
    mime_type: str,
    file_size_bytes: int,
    checksum: str,
    created_at: str,
    status: str = "PUBLISHED",
    processing_duration_ms: int | None = None,
) -> UniversalAssetMetadata:
    return UniversalAssetMetadata(
        asset_id=asset_id,
        asset_type=asset_type,  # type: ignore[arg-type]
        original_uri=original_uri,
        status=status,  # type: ignore[arg-type]
        file_name=file_name,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        checksum=checksum,
        created_at=created_at,
        processed_at=datetime.datetime.now(datetime.UTC).isoformat(),
        processing_duration_ms=processing_duration_ms,
    )


def build_technical(asset_id: str, asset_type: str, raw: dict[str, Any]) -> Any:
    if asset_type == "video":
        return VideoTechnicalMetadata(
            asset_id=asset_id,
            **{k: v for k, v in raw.items() if k in VideoTechnicalMetadata.model_fields},
        )
    if asset_type == "image":
        return ImageTechnicalMetadata(
            asset_id=asset_id,
            **{k: v for k, v in raw.items() if k in ImageTechnicalMetadata.model_fields},
        )
    if asset_type == "audio":
        return AudioTechnicalMetadata(
            asset_id=asset_id,
            **{k: v for k, v in raw.items() if k in AudioTechnicalMetadata.model_fields},
        )
    if asset_type == "document":
        return DocumentTechnicalMetadata(
            asset_id=asset_id,
            **{k: v for k, v in raw.items() if k in DocumentTechnicalMetadata.model_fields},
        )
    return {"asset_id": asset_id, "asset_type": asset_type, **raw}
