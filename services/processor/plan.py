"""Processing plan registry — Spec ."""

from typing import Literal

AssetType = Literal["video", "image", "audio", "document", "other"]

PLAN_REGISTRY: dict[AssetType, list[str]] = {
    "video": ["metadata", "transcode_1080p", "transcode_720p", "thumbnail"],
    "image": ["metadata", "resize", "thumbnail", "format_conversion"],
    "audio": ["metadata", "normalize", "format_conversion"],
    "document": ["integrity", "metadata_pages"],
    "other": ["metadata"],
}


def get_plan(asset_type: str) -> list[str]:
    """Return operations for asset_type. Raises ValueError for unknown type."""
    if asset_type not in PLAN_REGISTRY:
        raise ValueError(f"unsupported asset_type: {asset_type}")
    return list(PLAN_REGISTRY[asset_type])


def register_operation(asset_type: AssetType, operation: str) -> None:
    """Extensible registry — new operations without ingestion change ."""
    if operation not in PLAN_REGISTRY[asset_type]:
        PLAN_REGISTRY[asset_type].append(operation)
