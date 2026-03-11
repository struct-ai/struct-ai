def test_environment_is_ready() -> None:
    import pydantic
    import loguru

    assert bool(pydantic) and bool(loguru)
