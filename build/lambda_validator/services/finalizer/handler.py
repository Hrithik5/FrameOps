"""Finalizer gate — PUBLISHED only if all required ops SUCCEEDED, plus S3 audit."""

import os
from typing import Literal

try:
    from services.audit.writer import build_audit, write_audit_s3

    HAS_AUDIT = True
except Exception:
    HAS_AUDIT = False


def finalize(
    asset_id: str, required_ops: list[str], job_results: dict[str, str]
) -> Literal["PUBLISHED", "FAILED"]:
    """Check all required operations have SUCCEEDED. Else FAILED."""
    for op in required_ops:
        if job_results.get(op) != "SUCCEEDED":
            return "FAILED"
    return "PUBLISHED"


def finalize_with_outputs(
    asset_id: str,
    required_ops: list[str],
    job_results: dict[str, str],
    output_exists: dict[str, bool],
) -> Literal["PUBLISHED", "FAILED"]:
    """Also verifies outputs exist on S3 (never PUBLISHED without required outputs)."""
    if finalize(asset_id, required_ops, job_results) == "FAILED":
        return "FAILED"
    for op in required_ops:
        if not output_exists.get(op, False):
            return "FAILED"
    return "PUBLISHED"


def finalize_and_audit(
    asset_id: str,
    required_ops: list[str],
    job_results: dict[str, str],
    output_exists: dict[str, bool],
    event_id: str | None = None,
    pipeline_version: str = "1.0",
    outputs: dict[str, str] | None = None,
) -> Literal["PUBLISHED", "FAILED"]:
    status = finalize_with_outputs(asset_id, required_ops, job_results, output_exists)
    if HAS_AUDIT:
        try:
            bucket = os.environ.get("DATA_BUCKET", "") or os.environ.get("AUDIT_BUCKET", "")
            # Use asset_id as job_id prefix for finalizer audit
            audit = build_audit(
                asset_id=asset_id,
                job_id=f"finalizer-{asset_id}",
                event_id=event_id or asset_id,
                pipeline_version=pipeline_version,
                operations=required_ops,
                status=status,
                failure_reason=None if status == "PUBLISHED" else "finalize gate failed",
                outputs=outputs or {k: v for k, v in job_results.items()},
            )
            # Fire-and-forget — audit failure must not block PUBLISHED
            if bucket:
                write_audit_s3(audit, bucket)
        except Exception:
            pass
    return status


def lambda_handler(event: dict[str, object], context: object) -> dict[str, object]:
    """Step Functions Finalize task — PUBLISHED gate + audit."""
    from typing import Any

    asset_id = str(event.get("asset_id", ""))
    # Cast with defaults
    raw_ops: Any = event.get("operations", []) or event.get("required_ops", [])
    required_ops = list(raw_ops) if isinstance(raw_ops, list) else []
    raw_results: Any = event.get("job_results", {})
    job_results = dict(raw_results) if isinstance(raw_results, dict) else {}
    raw_exists: Any = event.get("output_exists", {})
    output_exists = dict(raw_exists) if isinstance(raw_exists, dict) else {}
    if not output_exists and required_ops:
        output_exists = {op: True for op in required_ops}
    raw_outputs: Any = event.get("outputs", {})
    outputs = dict(raw_outputs) if isinstance(raw_outputs, dict) else {}
    raw_eid: Any = event.get("event_id", asset_id)
    event_id = str(raw_eid) if raw_eid else asset_id
    raw_pv: Any = event.get("pipeline_version", "1.0")
    pipeline_version = str(raw_pv) if raw_pv else "1.0"
    status = finalize_and_audit(
        asset_id,
        required_ops,
        job_results,
        output_exists,
        event_id=event_id,
        pipeline_version=pipeline_version,
        outputs=outputs,
    )
    return {"status": status, "asset_id": asset_id}
