from services.observability.alarm_config import ALARMS
from services.observability.metrics import asset_published, dq_failure_rate, emit, sqs_depth


def test_metrics_emit():
    m = sqs_depth(42)
    payload = emit(m)
    assert payload["metric"] == "SQSQueueDepth" and payload["value"] == 42


def test_asset_published_dimension():
    m = asset_published("video")
    assert m.dimensions == {"asset_type": "video"}


def test_dq_rate():
    assert dq_failure_rate(2, 10) == 0.2
    assert dq_failure_rate(0, 0) == 0.0


def test_alarms_cover_spec():
    names = {a["name"] for a in ALARMS}
    assert "FrameOps-SQS-Backlog" in names
    assert "FrameOps-DLQ-Growth" in names
    assert "FrameOps-SFN-FailureSpike" in names
    # Spec §25: do not page on every individual asset failure — verify no per-asset alarm
    assert not any(a["metric"] == "AssetFailed" for a in ALARMS)
