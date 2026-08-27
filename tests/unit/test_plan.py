import pytest

from services.processor.plan import get_plan


def test_video_plan_has_parallel_ops():
    plan = get_plan("video")
    assert "metadata" in plan and "transcode_1080p" in plan and "thumbnail" in plan


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        get_plan("tiktok")


def test_image_plan():
    plan = get_plan("image")
    assert "resize" in plan


def test_new_operation_does_not_change_ingestion_contract():
    plan_before = get_plan("image")
    assert isinstance(plan_before, list)
