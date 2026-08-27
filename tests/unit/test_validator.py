from data.schemas.events import AssetCreatedEvent
from services.validator.core import validate_asset


def test_valid_proceed():
    evt = AssetCreatedEvent(
        event_type="ASSET_CREATED",
        event_version="1.0",
        asset_id="a1",
        asset_type="image",
        bucket="b",
        object_key="k",
        object_version="v1",
        checksum="c",
        created_at="2026-08-27T00:00:00Z",
    )
    res = validate_asset(evt)
    assert res.valid and res.action == "proceed"


def test_missing_key_quarantine():
    evt = AssetCreatedEvent(
        event_type="ASSET_CREATED",
        event_version="1.0",
        asset_id="a1",
        asset_type="video",
        bucket="b",
        object_key="k",
        object_version="v1",
        checksum="c",
        created_at="2026-08-27T00:00:00Z",
    )
    evt.object_key = ""
    res = validate_asset(evt)
    assert not res.valid and res.action == "quarantine"
