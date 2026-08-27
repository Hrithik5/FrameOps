"""Finalizer gate — PUBLISHED only if all required ops SUCCEEDED (Spec )."""

from typing import Literal


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
    """Also verifies outputs exist on S3 (Spec : never PUBLISHED without required outputs)."""
    if finalize(asset_id, required_ops, job_results) == "FAILED":
        return "FAILED"
    for op in required_ops:
        if not output_exists.get(op, False):
            return "FAILED"
    return "PUBLISHED"
