"""E2E: upload → validation → plan → workflow → Parquet → Athena (local)."""

import pathlib
import tempfile

from PIL import Image

from data.schemas.events import AssetCreatedEvent
from services.metadata.builder import build_universal
from services.metadata.parquet_writer import write_parquet
from services.processor.plan import get_plan
from services.validator.core import validate_asset
from workflows.processing.simulator import simulate


def test_e2e_image_published_to_parquet_and_athena():
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Ingest: S3 ObjectCreated → Event
        evt = AssetCreatedEvent(
            event_type="ASSET_CREATED",
            event_version="1.0",
            asset_id="asset-e2e-1",
            asset_type="image",
            bucket="frameops-assets-dev",
            object_key="raw/image/asset-e2e-1/source.jpg",
            object_version="v1",
            checksum="chk123",
            created_at="2026-08-27T00:00:00Z",
        )
        # 2. Validate
        assert validate_asset(evt).valid

        # 3. Plan
        plan = get_plan(evt.asset_type)
        assert "thumbnail" in plan

        # 4. Workflow: simulate parallel processing
        input_base = tmp + "/in"
        output_base = tmp + "/out"
        pathlib.Path(input_base).mkdir()
        pathlib.Path(output_base).mkdir()
        in_file = pathlib.Path(input_base) / evt.asset_id
        Image.new("RGB", (20, 20), "green").save(in_file, format="JPEG")

        result = simulate(evt.asset_id, evt.asset_type, plan[:2], input_base, output_base)
        # plan[:2] = metadata + resize => both should succeed
        assert result["status"] == "PUBLISHED"

        # 5. Build universal metadata
        meta = build_universal(
            asset_id=evt.asset_id,
            asset_type=evt.asset_type,
            original_uri=f"s3://{evt.bucket}/{evt.object_key}",
            file_name="source.jpg",
            mime_type="image/jpeg",
            file_size_bytes=12345,
            checksum=evt.checksum,
            created_at=evt.created_at,
            status=result["status"],
            processing_duration_ms=1200,
        )
        assert meta.status == "PUBLISHED"

        # 6. Write Parquet
        paths = write_parquet([meta.model_dump()], tmp + "/lake", "asset_metadata")
        assert len(paths) == 1 and pathlib.Path(paths[0]).exists()

        # 7. Athena via DuckDB
        try:
            import duckdb

            con = duckdb.connect()
            cnt = con.execute(f"SELECT count(*) FROM read_parquet({paths})").fetchone()[0]
            assert cnt == 1
        except ImportError:
            pass
