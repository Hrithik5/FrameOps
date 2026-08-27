"""Thumbnail / resize processor — Pillow based, retry-safe (Spec §15)."""

import pathlib
import time

from PIL import Image

from data.schemas.worker import WorkerInput, WorkerOutput


def run_thumbnail(inp: WorkerInput) -> WorkerOutput:
    start = time.time()
    try:
        out_path = pathlib.Path(inp.output_uri)
        # Idempotent: if output exists, short-circuit
        if out_path.exists():
            return WorkerOutput(
                asset_id=inp.asset_id,
                operation=inp.operation,
                status="SUCCEEDED",
                output_uri=inp.output_uri,
                duration_ms=0,
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(inp.input_uri)
        img.thumbnail((256, 256))
        # Ensure RGB for JPEG
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = bg  # type: ignore[assignment]
        # Handle extensionless output (Spec §22 deterministic URI has no ext) — default JPEG
        if not out_path.suffix:
            img.save(inp.output_uri, format="JPEG")
        else:
            img.save(inp.output_uri)
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


def run_resize(inp: WorkerInput, width: int = 1024, height: int = 1024) -> WorkerOutput:
    start = time.time()
    try:
        out_path = pathlib.Path(inp.output_uri)
        if out_path.exists():
            return WorkerOutput(
                asset_id=inp.asset_id,
                operation=inp.operation,
                status="SUCCEEDED",
                output_uri=inp.output_uri,
                duration_ms=0,
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(inp.input_uri)
        img.thumbnail((width, height))
        if not out_path.suffix:
            img.save(inp.output_uri, format="JPEG")
        else:
            img.save(inp.output_uri)
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
