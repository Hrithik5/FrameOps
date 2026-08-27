"""Audio normalize — stub copies file locally."""

import pathlib
import shutil
import time

from data.schemas.worker import WorkerInput, WorkerOutput


def run_normalize(inp: WorkerInput) -> WorkerOutput:
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
