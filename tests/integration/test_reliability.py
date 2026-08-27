"""Reliability injection — Spec Task 9."""

from PIL import Image

from data.schemas.worker import WorkerInput
from services.processor.thumbnail import run_thumbnail
from services.reliability.dlq import Queue, SQSMessage
from services.reliability.quarantine import quarantine_uri, should_quarantine
from services.reliability.retry import backoff_delay, classify_failure, should_retry


def test_transient_retries_then_succeeds():
    assert classify_failure("Timeout") == "transient"
    assert should_retry("transient", attempt=0) is True
    assert should_retry("transient", attempt=3) is False
    assert classify_failure("CorruptAsset") == "permanent"
    assert should_retry("permanent", attempt=0) is False


def test_backoff_bounded():
    assert backoff_delay(0) == 2.0
    assert backoff_delay(1) == 4.0
    assert backoff_delay(10) == 30.0  # capped


def test_corrupt_asset_quarantined():
    assert should_quarantine("permanent") is True
    assert should_quarantine("transient") is False
    uri = quarantine_uri("asset-123")
    assert "quarantine/asset-123" in uri


def test_dlq_after_5_failures():
    q = Queue(name="frameops-test")
    q.messages.append(SQSMessage(body="bad"))
    # Simulate 6 receives without ack
    for _ in range(6):
        msg = q.receive()
        if msg:
            q.nack(msg)
    assert len(q.dlq.messages) == 1
    assert len(q.messages) == 0


def test_partial_success_not_repeated(tmp_path):
    """Successful jobs idempotent; failed jobs retry independently."""
    in_path = tmp_path / "in.jpg"
    out_ok = tmp_path / "ok.jpg"
    out_fail = tmp_path / "fail.jpg"
    Image.new("RGB", (10, 10), "red").save(in_path)

    # Successful — second call idempotent 0 duration
    inp_ok = WorkerInput(
        asset_id="a1", operation="thumbnail", input_uri=str(in_path), output_uri=str(out_ok)
    )
    r1 = run_thumbnail(inp_ok)
    r2 = run_thumbnail(inp_ok)
    assert r1.status == "SUCCEEDED"
    assert r2.status == "SUCCEEDED" and r2.duration_ms == 0

    # Failed input — missing file → FAILED
    inp_fail = WorkerInput(
        asset_id="a1",
        operation="thumbnail",
        input_uri=str(tmp_path / "missing.jpg"),
        output_uri=str(out_fail),
    )
    rf = run_thumbnail(inp_fail)
    assert rf.status == "FAILED"
    # Successful still exists, failed did not create output
    assert out_ok.exists()
    assert not out_fail.exists()


def test_unknown_failure_terminal():
    assert classify_failure("WeirdError") == "unknown"
    assert should_quarantine("unknown") is True
    assert should_retry("unknown", 0) is False
