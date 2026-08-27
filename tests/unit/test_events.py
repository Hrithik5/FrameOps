import pytest

from data.schemas.events import AssetCreatedEvent


def test_asset_created_valid():
    evt = AssetCreatedEvent(
        event_type="ASSET_CREATED",
        event_version="1.0",
        asset_id="asset-123",
        asset_type="video",
        bucket="frameops-raw",
        object_key="raw/video/asset-123/source.mp4",
        object_version="v1",
        checksum="abc",
        created_at="2026-08-27T00:00:00Z",
    )
    assert evt.asset_type == "video"


def test_asset_created_rejects_unknown_type():
    with pytest.raises(Exception):
        AssetCreatedEvent(
            event_type="ASSET_CREATED",
            event_version="1.0",
            asset_id="a",
            asset_type="tiktok",  # type: ignore[arg-type]
            bucket="b",
            object_key="k",
            object_version="v1",
            checksum="c",
            created_at="2026-08-27T00:00:00Z",
        )


def test_breaking_change_requires_version_bump():
    with pytest.raises(Exception):
        AssetCreatedEvent.model_validate(
            {"event_type": "ASSET_CREATED", "event_version": "2.0", "asset_id": "x"}
        )
