"""Transcode stub — in Fargate would run ffmpeg; locally copies or simulates."""

import pathlib
import shutil
import time

from data.schemas.worker import WorkerInput, WorkerOutput


def run_transcode(inp: WorkerInput, profile: str = "1080p") -> WorkerOutput:
    """Simulate transcode: copy input to output if exists, else fail. Fargate runs real ffmpeg."""
    start = time.time()
    try:
        out = pathlib.Path(inp.output_uri)
        if out.exists():
            return WorkerOutput(
                asset_id=inp.asset_id,
                operation=inp.operation,
                status="SUCCEEDED",
                output_uri=inp.output_uri,
                duration_ms=0,
            )
        inp_path = pathlib.Path(inp.input_uri)
        if not inp_path.exists():
            raise FileNotFoundError(f"input not found: {inp.input_uri}")
        out.parent.mkdir(parents=True, exist_ok=True)
        # Simulate: copy file (real impl: ffmpeg -i input -vf scale... output)
        shutil.copy2(inp_path, out)
        dur = int((time.time() - start) * 1000)
        return WorkerOutput(
            asset_id=inp.asset_id,
            operation=inp.operation,
            status="SUCCEEDED",
            output_uri=inp.output_uri,
            duration_ms=dur,
        )
    except Exception as e:
        dur = int((time.time() - start) * 1000)
        return WorkerOutput(
            asset_id=inp.asset_id,
            operation=inp.operation,
            status="FAILED",
            output_uri=inp.output_uri,
            duration_ms=dur,
            error_code=str(e)[:500],
        )
