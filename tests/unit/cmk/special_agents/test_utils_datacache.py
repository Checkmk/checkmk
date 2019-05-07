# pylint: disable=protected-access
import pytest
from pathlib2 import Path

from cmk.special_agents.utils import DataCache


class KeksDose(DataCache):
    @property
    def cache_interval(self):
        return 5

    def get_validity_from_args(self, arg):
        return bool(arg)

    def get_live_data(self, arg):
        return "live data"


def test_datacache_init(tmpdir):
    tcache = KeksDose(tmpdir, 'test')
    assert isinstance(tcache._cache_file_dir, Path)
    assert isinstance(tcache._cache_file, Path)
    assert not tcache.debug

    tc_debug = KeksDose(tmpdir, 'test', debug=True)
    assert tc_debug.debug

    with pytest.raises(TypeError):
        DataCache('foo', 'bar')  # pylint: disable=abstract-class-instantiated


def test_datacache_timestamp(tmpdir):
    tcache = KeksDose(tmpdir, 'test')

    assert tcache.cache_timestamp is None  # file doesn't exist yet

    tcache._write_to_cache('')
    assert tcache.cache_timestamp == tcache._cache_file.stat().st_mtime


def test_datacache_valid(monkeypatch, tmpdir):
    tcache = KeksDose(tmpdir, 'test')
    tcache._write_to_cache('cached data')

    valid_time = tcache.cache_timestamp + tcache.cache_interval - 1
    monkeypatch.setattr("time.time", lambda: valid_time)

    assert tcache._cache_is_valid()
    # regular case
    assert tcache.get_data(True) == 'cached data'
    # force live data
    assert tcache.get_data(True, use_cache=False) == 'live data'
    # cache is valid, but get_validity_from_args wants live data
    assert tcache.get_data(False) == 'live data'
    # now live data should be in the cache file
    assert tcache.get_data(True) == 'live data'


def test_datacache_validity(monkeypatch, tmpdir):
    tcache = KeksDose(tmpdir, 'test')
    tcache._write_to_cache('cached data')

    invalid_time = tcache.cache_timestamp + tcache.cache_interval + 1
    monkeypatch.setattr("time.time", lambda: invalid_time)

    assert not tcache._cache_is_valid()
    assert tcache.get_data(True) == 'live data'
