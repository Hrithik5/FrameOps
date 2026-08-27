from services.processor.idempotency import deterministic_asset_id, job_id_for, output_uri_for


def test_deterministic_asset_id():
    a = deterministic_asset_id("b", "k", "v1")
    b = deterministic_asset_id("b", "k", "v1")
    c = deterministic_asset_id("b", "k", "v2")
    assert a == b
    assert a != c


def test_output_uri_deterministic():
    u1 = output_uri_for("asset-1", "thumbnail", "1.0")
    u2 = output_uri_for("asset-1", "thumbnail", "1.0")
    u3 = output_uri_for("asset-1", "thumbnail", "2.0")
    assert u1 == u2
    assert u1 != u3


def test_job_id_deterministic():
    j1 = job_id_for("a1", "metadata", "1.0")
    j2 = job_id_for("a1", "metadata", "1.0")
    assert j1 == j2
