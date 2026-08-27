import tempfile

import pyarrow.parquet as pq

from services.metadata.parquet_writer import read_parquet, write_parquet


def test_parquet_write_and_read():
    with tempfile.TemporaryDirectory() as tmp:
        records = [
            {
                "asset_id": "a1",
                "asset_type": "video",
                "file_size_bytes": 100,
                "status": "PUBLISHED",
            },
            {
                "asset_id": "a2",
                "asset_type": "image",
                "file_size_bytes": 200,
                "status": "PUBLISHED",
            },
        ]
        paths = write_parquet(records, tmp, "asset_metadata")
        assert len(paths) == 1
        # Verify snappy
        pf = pq.ParquetFile(paths[0])
        assert pf.metadata.row_group(0).column(0).compression == "SNAPPY"
        table = read_parquet(tmp, "asset_metadata")
        assert table.num_rows == 2


def test_dq_rejects_zero_file_size(tmp_path=None):
    import tempfile

    import pytest

    with tempfile.TemporaryDirectory() as tmp, pytest.raises(ValueError):
        write_parquet(
            [{"asset_id": "a1", "asset_type": "video", "file_size_bytes": 0}],
            tmp,
            "asset_metadata",
        )


def test_athena_query_via_duckdb():
    import tempfile

    try:
        import duckdb
    except ImportError:
        return
    with tempfile.TemporaryDirectory() as tmp:
        write_parquet(
            [{"asset_id": "a1", "asset_type": "video", "file_size_bytes": 100}],
            tmp,
            "asset_metadata",
        )
        # read via duckdb local parquet query (simulates Athena)
        import glob

        files = glob.glob(tmp + "/asset_metadata/**/*.parquet", recursive=True)
        con = duckdb.connect()
        result = con.execute(f"SELECT count(*) FROM read_parquet({files})").fetchone()
        assert result[0] == 1
