import socket
import pytest  # type: ignore
from pathlib2 import Path

from testlib.base import Scenario
import cmk.base.ip_lookup as ip_lookup


@pytest.fixture()
def _cache_file():
    p = Path(ip_lookup._cache_path())
    p.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member

    yield p

    if p.exists():
        p.unlink()


def test_get_ip_lookup_cache_not_existing(_cache_file):
    if _cache_file.exists():
        _cache_file.unlink()

    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()

    assert ip_lookup_cache == {}


def test_get_ip_lookup_cache_invalid_syntax(_cache_file):
    with _cache_file.open(mode="w", encoding="utf-8") as f:
        f.write(u"{...")

    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()

    assert ip_lookup_cache == {}


def test_get_ip_lookup_cache_existing(_cache_file):
    cache_id1 = "host1", 4
    with _cache_file.open(mode="w", encoding="utf-8") as f:
        f.write(u"%r" % {cache_id1: "1"})

    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()

    assert ip_lookup_cache == {cache_id1: "1"}


def test_update_ip_lookup_cache_empty_file(_cache_file):
    cache_id = "host1", 4
    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()
    ip_lookup_cache.update_cache(cache_id, "127.0.0.1")

    cache = ip_lookup._load_ip_lookup_cache(lock=False)
    assert cache[cache_id] == "127.0.0.1"

    cache = ip_lookup._load_ip_lookup_cache(lock=False)
    assert cache[cache_id] == "127.0.0.1"


def test_update_ip_lookup_cache_extend_existing_file(_cache_file):
    cache_id1 = "host1", 4
    cache_id2 = "host2", 4

    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()
    ip_lookup_cache.update_cache(cache_id1, "127.0.0.1")
    ip_lookup_cache.update_cache(cache_id2, "127.0.0.2")

    cache = ip_lookup._load_ip_lookup_cache(lock=False)
    assert cache[cache_id1] == "127.0.0.1"
    assert cache[cache_id2] == "127.0.0.2"


def test_update_ip_lookup_cache_update_existing_entry(_cache_file):
    cache_id1 = "host1", 4
    cache_id2 = "host2", 4

    with _cache_file.open(mode="w", encoding="utf-8") as f:
        f.write(u"%r" % {cache_id1: "1", cache_id2: "2"})

    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()
    ip_lookup_cache.update_cache(cache_id1, "127.0.0.1")

    cache = ip_lookup._load_ip_lookup_cache(lock=False)
    assert cache[cache_id1] == "127.0.0.1"
    assert cache[cache_id2] == "2"


def test_ip_lookup_cache_update_without_persistence(_cache_file):
    cache_id1 = "host1", 4

    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()
    ip_lookup_cache.persist_on_update = False
    ip_lookup_cache.update_cache(cache_id1, "127.0.0.1")

    assert ip_lookup_cache[cache_id1] == "127.0.0.1"
    assert not _cache_file.exists()


def test_load_legacy_lookup_cache(_cache_file):
    cache_id1 = "host1", 4
    cache_id2 = "host2", 4

    with _cache_file.open("w", encoding="utf-8") as f:
        f.write(u"%r" % {"host1": "127.0.0.1", "host2": "127.0.0.2"})

    cache = ip_lookup._load_ip_lookup_cache(lock=False)
    assert cache[cache_id1] == "127.0.0.1"
    assert cache[cache_id2] == "127.0.0.2"


def test_update_dns_cache(monkeypatch, _cache_file):
    def _getaddrinfo(host, port, family=None, socktype=None, proto=None, flags=None):
        # Needs to return [(family, type, proto, canonname, sockaddr)] but only
        # caring about the address
        return {
            ("blub", socket.AF_INET): [(family, None, None, None, ("127.0.0.13", 1337))],
            ("bla", socket.AF_INET): [(family, None, None, None, ("127.0.0.37", 1337))],
            ("dual", socket.AF_INET): [(family, None, None, None, ("127.0.0.42", 1337))],
        }[(host, family)]

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)

    ts = Scenario()
    ts.add_host("blub", tags={"criticality": "offline"})
    ts.add_host("bla")
    ts.add_host("dual", tags={"address_family": "ip-v4v6"})
    ts.apply(monkeypatch)

    assert ip_lookup.update_dns_cache() == (3, ["dual"])

    # Check persisted data
    cache = ip_lookup._load_ip_lookup_cache(lock=False)
    assert cache[("blub", 4)] == "127.0.0.13"
    assert ("dual", 6) not in cache


def test_clear_ip_lookup_cache(_cache_file):
    with _cache_file.open(mode="w", encoding="utf-8") as f:
        f.write(u"%r" % {("host1", 4): "127.0.0.1"})

    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()
    assert ip_lookup_cache[("host1", 4)] == "127.0.0.1"

    ip_lookup._clear_ip_lookup_cache(ip_lookup_cache)

    assert len(ip_lookup_cache) == 0
    assert not _cache_file.exists()


def test_get_dns_cache_lookup_hosts(monkeypatch):
    ts = Scenario()
    ts.add_host("blub", tags={"criticality": "offline"})
    ts.add_host("bla")
    ts.add_host("dual", tags={"address_family": "ip-v4v6"})

    ts.apply(monkeypatch)

    assert sorted(ip_lookup._get_dns_cache_lookup_hosts()) == sorted([
        ('bla', 4),
        ('dual', 4),
        ('dual', 6),
        ('blub', 4),
    ])
