import pytest  # type: ignore
import testlib
from testlib.base import Scenario


@pytest.fixture(scope="module")
def check_manager():
    return testlib.CheckManager()


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base
    import cmk_base.caching
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())

    ts = Scenario()
    ts.add_host("non-existent-testhost")
    ts.apply(monkeypatch)
