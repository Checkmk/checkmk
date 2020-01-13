import pytest


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    import cmk.base.config
    import cmk.base.caching
    monkeypatch.setattr(cmk.base, "config_cache", cmk.base.caching.CacheManager())
    monkeypatch.setattr(cmk.base, "runtime_cache", cmk.base.caching.CacheManager())
