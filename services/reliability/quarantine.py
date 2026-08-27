"""Quarantine handling — Spec ."""

import pathlib


def quarantine_uri(asset_id: str, bucket: str = "frameops-assets-dev") -> str:
    return f"s3://{bucket}/quarantine/{asset_id}/"


def quarantine_local_path(asset_id: str, base: str = "/tmp/frameops/quarantine") -> pathlib.Path:
    p = pathlib.Path(base) / asset_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def should_quarantine(failure_class: str) -> bool:
    return failure_class in ("permanent", "unknown")
