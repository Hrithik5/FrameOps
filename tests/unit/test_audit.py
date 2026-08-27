import pathlib

from services.audit.writer import AuditRecord, audit_key, build_audit, write_audit_local


def test_audit_key_year_month_day():
    rec = build_audit(
        asset_id="a1",
        job_id="j1",
        event_id="e1",
        pipeline_version="1.0",
        operations=["thumbnail"],
        started_at="2026-08-27T10:00:00Z",
        status="SUCCEEDED",
    )
    key = audit_key(rec)
    assert "audit/year=2026/month=08/day=27/a1/j1.json" in key


def test_write_audit_local(tmp_path):
    rec = AuditRecord(
        asset_id="a1",
        job_id="j1",
        event_id="e1",
        pipeline_version="1.0",
        operations=["metadata"],
        started_at="2026-08-27T10:00:00Z",
        status="PUBLISHED",
        outputs={"thumbnail": "s3://b/k"},
    )
    path = write_audit_local(rec, str(tmp_path))
    p = pathlib.Path(path)
    assert p.exists()
    assert (p.parent / "j1.json").exists()
    # Verify content
    import json

    data = json.loads(p.read_text())
    assert data["asset_id"] == "a1"
    assert data["job_id"] == "j1"
    assert data["status"] == "PUBLISHED"
    assert data["outputs"]["thumbnail"] == "s3://b/k"


def test_build_audit_failure():
    rec = build_audit(
        asset_id="a1",
        job_id="j2",
        event_id="e1",
        status="FAILED",
        failure_reason="corrupt",
        started_at="2026-08-27T10:00:00Z",
    )
    assert rec.failure_reason == "corrupt"
    assert rec.status == "FAILED"
