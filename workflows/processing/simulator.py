"""Local Step Functions simulator — runs processors in parallel threads."""

import concurrent.futures
from typing import Any

from data.schemas.worker import WorkerInput
from services.finalizer.handler import finalize
from services.processor.audio import run_normalize
from services.processor.document import run_integrity
from services.processor.metadata import run_metadata
from services.processor.thumbnail import run_resize, run_thumbnail
from services.processor.transcode import run_transcode

OP_TO_FN = {
    "metadata": run_metadata,
    "thumbnail": run_thumbnail,
    "resize": run_resize,
    "format_conversion": run_thumbnail,
    "transcode_1080p": lambda inp: run_transcode(inp, "1080p"),
    "transcode_720p": lambda inp: run_transcode(inp, "720p"),
    "normalize": run_normalize,
    "integrity": run_integrity,
    "metadata_pages": run_metadata,
}


def simulate(
    asset_id: str,
    asset_type: str,
    operations: list[str],
    input_base: str,
    output_base: str,
) -> dict[str, Any]:
    """Run operations in parallel (thread pool), then finalize. Returns execution result."""
    job_results: dict[str, str] = {}

    def _run(op: str) -> tuple[str, str]:
        fn = OP_TO_FN.get(op, run_metadata)
        inp = WorkerInput(
            asset_id=asset_id,
            operation=op,
            input_uri=f"{input_base}/{asset_id}",
            output_uri=f"{output_base}/{asset_id}/{op}/output",
        )
        out = fn(inp)  # type: ignore[operator]
        return op, out.status

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_run, op): op for op in operations}
        for fut in concurrent.futures.as_completed(futures):
            op, status = fut.result()
            job_results[op] = status

    status = finalize(asset_id, operations, job_results)
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "status": status,
        "job_results": job_results,
        "operations": operations,
    }
