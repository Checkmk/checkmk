import pytest  # type: ignore
import testlib
from testlib.base import Scenario


@pytest.fixture(scope="module")
def check_manager():
    return testlib.CheckManager()


# patch cmk.utils.paths
@pytest.fixture(autouse=True, scope="function")
def patch_cmk_utils_paths(monkeypatch, tmp_path):
    import cmk.utils.paths
    var_dir_path = tmp_path / 'var' / 'check_mk'
    # don't mkdir, check should be able to handle that.
    monkeypatch.setattr(cmk.utils.paths, "var_dir", str(var_dir_path))


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
