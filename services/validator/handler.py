"""Lambda validator handler — thin wrapper over pure core (Spec §8)."""

import json
from typing import Any

from data.schemas.events import AssetCreatedEvent
from services.validator.core import validate_asset


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process SQS batch of ASSET_CREATED events. No heavy compute."""
    results: list[dict[str, Any]] = []
    for record in event.get("Records", []):
        try:
            body_raw = record.get("body", "")
            if isinstance(body_raw, str):
                body = json.loads(body_raw) if body_raw else record
            else:
                body = body_raw
            # EventBridge wraps S3 event differently; support direct dict too
            if isinstance(body, dict) and "Records" in body:
                body = body
            evt = AssetCreatedEvent.model_validate(body)
        except Exception as e:
            results.append({"status": "quarantine", "reason": f"invalid event: {e}"})
            continue

        res = validate_asset(evt)
        if not res.valid:
            results.append({"asset_id": evt.asset_id, "status": "quarantine", "reason": res.reason})
        else:
            # In real AWS: DynamoDB conditional Put + Step Functions StartExecution
            # Here we return proceed so callers can assert idempotency
            results.append({"asset_id": evt.asset_id, "status": "proceed"})

    return {"results": results}
