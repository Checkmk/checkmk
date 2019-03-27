import pytest

import cmk
import testlib


@pytest.fixture(scope="module")
def check_manager():
    return testlib.CheckManager()


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base
    import cmk_base.caching
    import cmk_base.config
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())

    monkeypatch.setattr(cmk_base.config, "all_hosts", ["non-existent-testhost"])
    monkeypatch.setattr(cmk_base.config, "host_paths", {"non-existent-testhost": "/"})
    cmk_base.config.get_config_cache().initialize()
