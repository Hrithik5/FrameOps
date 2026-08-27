"""S3 audit writer — per-run auditable history.

Writes:
  s3://<bucket>/audit/year=YYYY/month=MM/day=DD/<asset_id>/<job_id>.json

Contains: asset_id, job_id, event_id, pipeline_version, operations,
          started_at, completed_at, status, failure_reason, outputs
"""

import datetime
import json
import pathlib

from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    asset_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    pipeline_version: str = Field(default="1.0")
    operations: list[str] = Field(default_factory=list)
    started_at: str = Field(min_length=1)
    completed_at: str | None = None
    status: str = Field(description="PUBLISHED, FAILED, RUNNING, etc.")
    failure_reason: str | None = None
    outputs: dict[str, str] = Field(default_factory=dict)


def audit_key(record: AuditRecord, prefix: str = "audit") -> str:
    dt = datetime.datetime.now(datetime.UTC)
    # Use started_at year/month/day if available, else now
    import contextlib

    with contextlib.suppress(Exception):
        dt = datetime.datetime.fromisoformat(record.started_at.replace("Z", "+00:00"))
    return (
        f"{prefix}/year={dt.year}/month={dt.month:02d}/day={dt.day:02d}/"
        f"{record.asset_id}/{record.job_id}.json"
    )


def write_audit_local(record: AuditRecord, base_path: str, prefix: str = "audit") -> str:
    """Write to local filesystem (for tests, no AWS). Returns file path."""
    key = audit_key(record, prefix)
    out = pathlib.Path(base_path) / key
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record.model_dump(), indent=2))
    return str(out)


def write_audit_s3(record: AuditRecord, bucket: str, prefix: str = "audit") -> str:
    """Write to S3 via boto3. Returns s3://... key. No-op if bucket empty."""
    if not bucket:
        return write_audit_local(record, "/tmp/frameops-audit", prefix)
    import boto3

    key = audit_key(record, prefix)
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(record.model_dump()).encode(),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )
    return f"s3://{bucket}/{key}"


def build_audit(
    asset_id: str,
    job_id: str,
    event_id: str,
    pipeline_version: str = "1.0",
    operations: list[str] | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    status: str = "SUCCEEDED",
    failure_reason: str | None = None,
    outputs: dict[str, str] | None = None,
) -> AuditRecord:
    now = datetime.datetime.now(datetime.UTC).isoformat()
    return AuditRecord(
        asset_id=asset_id,
        job_id=job_id,
        event_id=event_id,
        pipeline_version=pipeline_version,
        operations=operations or [],
        started_at=started_at or now,
        completed_at=completed_at or now,
        status=status,
        failure_reason=failure_reason,
        outputs=outputs or {},
    )
