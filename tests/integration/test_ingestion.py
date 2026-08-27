import json

from services.validator.handler import lambda_handler


def test_duplicate_event_idempotent():
    body = json.dumps(
        {
            "event_type": "ASSET_CREATED",
            "event_version": "1.0",
            "asset_id": "a1",
            "asset_type": "image",
            "bucket": "b",
            "object_key": "k",
            "object_version": "v1",
            "checksum": "c",
            "created_at": "2026-08-27T00:00:00Z",
        }
    )
    evt = {"Records": [{"body": body}, {"body": body}]}
    res = lambda_handler(evt, None)
    assert len(res["results"]) == 2
    assert all(r["status"] == "proceed" for r in res["results"])


def test_quarantine_on_invalid():
    body = json.dumps(
        {
            "event_type": "ASSET_CREATED",
            "event_version": "1.0",
            "asset_id": "",
            "asset_type": "video",
            "bucket": "b",
            "object_key": "",
            "object_version": "v1",
            "checksum": "",
            "created_at": "",
        }
    )
    evt = {"Records": [{"body": body}]}
    res = lambda_handler(evt, None)
    assert res["results"][0]["status"] == "quarantine"
