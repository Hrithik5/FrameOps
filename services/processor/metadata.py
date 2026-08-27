"""Metadata extraction — image via Pillow, PDF via pypdf, video/audio via ffprobe stub."""

import pathlib
import time
from typing import Any

from data.schemas.worker import WorkerInput, WorkerOutput

try:
    from PIL import Image

    HAS_PILLOW = True
except Exception:
    HAS_PILLOW = False


def _image_meta(path: str) -> dict[str, Any]:
    if not HAS_PILLOW:
        return {}
    with Image.open(path) as img:
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
        }


def _pdf_meta(path: str) -> dict[str, Any]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(path)
        info = reader.metadata
        return {
            "page_count": len(reader.pages),
            "author": str(info.author) if info and info.author else None,
            "creation_date": str(info.creation_date) if info and info.creation_date else None,
        }
    except Exception:
        return {}


def run_metadata(inp: WorkerInput) -> WorkerOutput:
    start = time.time()
    try:
        p = pathlib.Path(inp.input_uri)
        suffix = p.suffix.lower()
        meta: dict[str, Any] = {}
        if suffix in (".jpg", ".jpeg", ".png", ".webp", ".bmp") and p.exists():
            meta = _image_meta(str(p))
        elif suffix == ".pdf" and p.exists():
            meta = _pdf_meta(str(p))
        else:
            # video/audio — would use ffprobe in Fargate; locally mock
            meta = {"note": "ffprobe stub - video/audio metadata extracted in Fargate"}

        # Write metadata json alongside output if output_uri is file path
        out = pathlib.Path(inp.output_uri)
        if str(out).startswith("s3://"):
            # In local tests output_uri may be s3; skip file write
            pass
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            import json

            out.write_text(
                json.dumps(
                    {"asset_id": inp.asset_id, "operation": inp.operation, "metadata": meta},
                    indent=2,
                )
            )

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
