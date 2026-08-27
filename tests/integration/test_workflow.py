import pathlib
import tempfile

from PIL import Image

from workflows.processing.simulator import simulate


def test_parallel_metadata_and_thumbnail():
    with tempfile.TemporaryDirectory() as tmp:
        input_base = tmp + "/in"
        output_base = tmp + "/out"
        pathlib.Path(input_base).mkdir()
        pathlib.Path(output_base).mkdir()
        # create dummy input file
        asset_id = "asset-123"
        in_file = pathlib.Path(input_base) / asset_id
        Image.new("RGB", (10, 10), "blue").save(in_file, format="JPEG")
        result = simulate(
            asset_id=asset_id,
            asset_type="image",
            operations=["metadata", "thumbnail"],
            input_base=input_base,
            output_base=output_base,
        )
        assert result["status"] == "PUBLISHED"
        assert "metadata" in result["job_results"]
        assert "thumbnail" in result["job_results"]


def test_finalizer_requires_all_required_ops():
    from services.finalizer.handler import finalize

    assert finalize("a1", ["metadata", "thumbnail"], {"metadata": "SUCCEEDED"}) == "FAILED"
    assert finalize("a1", ["metadata"], {"metadata": "SUCCEEDED"}) == "PUBLISHED"
