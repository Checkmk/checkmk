import pytest

# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base.config
    import cmk_base.caching
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())

