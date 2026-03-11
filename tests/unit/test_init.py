def test_environment_is_ready() -> None:
    import loguru
    import pydantic

    assert bool(pydantic) and bool(loguru)
