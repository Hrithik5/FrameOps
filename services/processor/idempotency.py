"""Idempotency helpers — Spec ."""

import hashlib


def deterministic_asset_id(bucket: str, key: str, version: str) -> str:
    """Stable id for logical asset/version — duplicate events map to same id."""
    raw = f"{bucket}/{key}#{version}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"asset-{h}"


def output_uri_for(
    asset_id: str,
    operation: str,
    pipeline_version: str = "1.0",
    bucket: str = "frameops-assets-dev",
) -> str:
    """Deterministic output URI — retries do not create duplicate derivatives."""
    return f"s3://{bucket}/processed/{asset_id}/{operation}/v{pipeline_version}/output"


def dynamodb_pk(asset_id: str) -> str:
    return f"ASSET#{asset_id}"


def dynamodb_sk_job(job_id: str) -> str:
    return f"JOB#{job_id}"


def job_id_for(asset_id: str, operation: str, pipeline_version: str = "1.0") -> str:
    raw = f"{asset_id}:{operation}:{pipeline_version}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"job-{h}"
