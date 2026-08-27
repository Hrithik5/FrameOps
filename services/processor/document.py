"""Document integrity — validates PDF readable."""

import pathlib
import time

from data.schemas.worker import WorkerInput, WorkerOutput


def run_integrity(inp: WorkerInput) -> WorkerOutput:
    start = time.time()
    try:
        p = pathlib.Path(inp.input_uri)
        if not p.exists():
            raise FileNotFoundError(f"input not found: {inp.input_uri}")
        # Try reading PDF
        if p.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(p))
            _ = len(reader.pages)
        # Write integrity marker
        out = pathlib.Path(inp.output_uri)
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists():
            out.write_text('{"integrity": "ok"}')
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
