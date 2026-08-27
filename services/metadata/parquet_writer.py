"""Parquet writer with Snappy + year/month/day partitioning + DQ (Spec §20, §24)."""

import datetime
import pathlib
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def _validate_records(records: list[dict[str, Any]], dataset: str) -> None:
    for r in records:
        if not r.get("asset_id"):
            raise ValueError(f"{dataset}: asset_id required")
        if r.get("file_size_bytes") is not None and r["file_size_bytes"] <= 0:
            raise ValueError(f"{dataset}: file_size_bytes must be >0")
        if r.get("asset_type") and r["asset_type"] not in (
            "video",
            "image",
            "audio",
            "document",
            "other",
        ):
            raise ValueError(f"{dataset}: invalid asset_type {r['asset_type']}")


def write_parquet(records: list[dict[str, Any]], base_path: str, dataset: str) -> list[str]:
    """Write records partitioned by year/month/day, Snappy. Returns file paths."""
    if not records:
        return []
    _validate_records(records, dataset)
    now = datetime.datetime.now(datetime.UTC)
    part = f"year={now.year}/month={now.month:02d}/day={now.day:02d}"
    out_dir = pathlib.Path(base_path) / dataset / part
    out_dir.mkdir(parents=True, exist_ok=True)

    # Convert to pyarrow table
    table = pa.Table.from_pylist(records)
    out_file = out_dir / "part-001.parquet"
    pq.write_table(table, str(out_file), compression="snappy")
    return [str(out_file)]


def read_parquet(base_path: str, dataset: str) -> pa.Table:
    pattern = pathlib.Path(base_path) / dataset / "**" / "*.parquet"
    import glob

    files = glob.glob(str(pattern), recursive=True)
    if not files:
        return pa.table({})
    tables = [pq.read_table(f) for f in files]
    return pa.concat_tables(tables) if len(tables) > 1 else tables[0]
