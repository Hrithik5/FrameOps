import pytest

from data.schemas.asset import UniversalAssetMetadata


def test_universal_valid():
    m = UniversalAssetMetadata(
        asset_id="a1",
        asset_type="video",
        original_uri="s3://b/k",
        status="PUBLISHED",
        file_name="f.mp4",
        mime_type="video/mp4",
        file_size_bytes=100,
        checksum="c",
        created_at="2026-08-27T00:00:00Z",
    )
    assert m.file_size_bytes == 100


def test_zero_file_size_rejected():
    with pytest.raises(Exception):
        UniversalAssetMetadata(
            asset_id="a1",
            asset_type="video",
            original_uri="s3://b/k",
            status="PUBLISHED",
            file_name="f.mp4",
            mime_type="video/mp4",
            file_size_bytes=0,
            checksum="c",
            created_at="2026-08-27T00:00:00Z",
        )
