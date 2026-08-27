def test_package_importable():
    import services

    assert services is not None
