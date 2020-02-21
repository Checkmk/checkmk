import pytest  # type: ignore[import]


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    from cmk.base import config_cache as _config_cache, runtime_cache as _runtime_cache
    _config_cache.reset()
    _runtime_cache.reset()
