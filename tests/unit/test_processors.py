import pathlib

from PIL import Image

from data.schemas.worker import WorkerInput
from services.processor.thumbnail import run_thumbnail


def test_thumbnail_idempotent_and_retry_safe(tmp_path):
    in_path = tmp_path / "in.jpg"
    out_path = tmp_path / "out.jpg"
    Image.new("RGB", (10, 10), "red").save(in_path)
    inp = WorkerInput(
        asset_id="asset-1", operation="thumbnail", input_uri=str(in_path), output_uri=str(out_path)
    )
    out1 = run_thumbnail(inp)
    out2 = run_thumbnail(inp)
    assert out1.status == "SUCCEEDED" and out2.status == "SUCCEEDED"
    assert pathlib.Path(out_path).exists()
    # second is idempotent with 0 duration
    assert out2.duration_ms == 0
