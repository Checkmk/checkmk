import pytest  # type: ignore[import]


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    import cmk.base
    cmk.base.config_cache.reset()
    cmk.base.runtime_cache.reset()
