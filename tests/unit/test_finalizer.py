from services.finalizer.handler import finalize, finalize_with_outputs


def test_finalizer_requires_all_required_ops():
    assert finalize("a1", ["metadata", "thumbnail"], {"metadata": "SUCCEEDED"}) == "FAILED"
    assert finalize("a1", ["metadata"], {"metadata": "SUCCEEDED"}) == "PUBLISHED"


def test_finalizer_with_outputs():
    assert (
        finalize_with_outputs("a1", ["metadata"], {"metadata": "SUCCEEDED"}, {"metadata": True})
        == "PUBLISHED"
    )
    assert (
        finalize_with_outputs("a1", ["metadata"], {"metadata": "SUCCEEDED"}, {"metadata": False})
        == "FAILED"
    )
