#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeAlias

import pytest
from pytest import MonkeyPatch

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.exceptions import MKIPAddressLookupError
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils import ip_lookup
from cmk.utils.caching import cache_manager
from cmk.utils.tags import TagGroupID, TagID

from cmk.base import config

_IPLookupCacheMapping: TypeAlias = dict[
    ip_lookup.IPLookupCacheId, HostAddress | MKIPAddressLookupError
]
_PersistedCache: TypeAlias = dict[ip_lookup.IPLookupCacheId, str | None]


@pytest.fixture(autouse=True)
def no_io_ip_lookup_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(ip_lookup.IPLookupCache, "PATH", tmp_path / "cache")


def patch_config_cache(monkeypatch: MonkeyPatch, cache: _IPLookupCacheMapping) -> None:
    monkeypatch.setattr(cache_manager, "obtain_cache", lambda _x: cache)


def patch_persisted_cache(monkeypatch: MonkeyPatch, cache: _PersistedCache) -> None:
    monkeypatch.setattr(ip_lookup, "_get_ip_lookup_cache", lambda: cache)


def patch_actual_lookup(monkeypatch: MonkeyPatch, mapping: _PersistedCache) -> None:
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda hn, _a, fm: [[0, 0, 0, 0, [mapping[(hn, fm)]]]]
    )


def test_ip_address_of(monkeypatch: MonkeyPatch) -> None:
    _FALLBACK_ADDRESS_IPV4: Final = "0.0.0.0"
    _FALLBACK_ADDRESS_IPV6: Final = "::"
    localhost = HostName("localhost")
    no_ip = HostName("no_ip")
    dual_stack = HostName("dual_stack")
    cluster = HostName("cluster")
    bad_host = HostName("bad_host")
    undiscoverable = HostName("undiscoverable")

    ts = Scenario()
    ts.add_host(localhost)
    ts.add_host(HostName(undiscoverable))
    ts.add_host(HostName(no_ip), {TagGroupID("address_family"): TagID("no-ip")})
    ts.add_host(HostName(dual_stack), {TagGroupID("address_family"): TagID("ip-v4v6")})
    ts.add_cluster(HostName(cluster))
    config_cache = ts.apply(monkeypatch)
    ip_lookup_config = config_cache.ip_lookup_config()
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, family=None, *args, **kwargs: {
            (localhost, socket.AF_INET): [(family, None, None, None, ("127.0.0.1", 0))],
            (localhost, socket.AF_INET6): [(family, None, None, None, ("::1", 0))],
        }[(host, family)],
    )

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=lambda *a: None,
    )

    assert ip_lookup_config.default_address_family(localhost) is socket.AddressFamily.AF_INET
    assert ip_lookup_config.ip_stack_config(localhost) is ip_lookup.IPStackConfig.IPv4

    assert (
        ip_address_of(
            localhost,
            socket.AddressFamily.AF_INET,
        )
        == "127.0.0.1"
    )
    assert (
        ip_address_of(
            localhost,
            socket.AddressFamily.AF_INET6,
        )
        == "::1"
    )

    assert ip_lookup_config.default_address_family(no_ip) is socket.AddressFamily.AF_INET
    assert ip_lookup_config.ip_stack_config(no_ip) is ip_lookup.IPStackConfig.NO_IP

    assert ip_lookup_config.default_address_family(dual_stack) is socket.AddressFamily.AF_INET
    assert ip_lookup_config.ip_stack_config(dual_stack) is ip_lookup.IPStackConfig.DUAL_STACK
    assert (
        ip_address_of(
            dual_stack,
            socket.AddressFamily.AF_INET,
        )
        == _FALLBACK_ADDRESS_IPV4
    )
    assert (
        ip_address_of(
            dual_stack,
            socket.AddressFamily.AF_INET6,
        )
        == _FALLBACK_ADDRESS_IPV6
    )

    assert ip_lookup_config.default_address_family(cluster) is socket.AddressFamily.AF_INET
    assert (
        ip_lookup_config.ip_stack_config(cluster) is ip_lookup.IPStackConfig.IPv4
    )  # That's strange
    assert (
        ip_address_of(
            cluster,
            socket.AddressFamily.AF_INET,
        )
        == ""
    )
    assert (
        ip_address_of(
            cluster,
            socket.AddressFamily.AF_INET6,
        )
        == ""
    )

    assert ip_lookup_config.default_address_family(bad_host) is socket.AddressFamily.AF_INET
    assert (
        ip_lookup_config.ip_stack_config(bad_host) is ip_lookup.IPStackConfig.IPv4
    )  # That's strange
    assert (
        ip_address_of(
            bad_host,
            socket.AddressFamily.AF_INET,
        )
        == _FALLBACK_ADDRESS_IPV4
    )
    assert (
        ip_address_of(
            bad_host,
            socket.AddressFamily.AF_INET6,
        )
        == _FALLBACK_ADDRESS_IPV6
    )

    assert ip_lookup_config.default_address_family(undiscoverable) is socket.AddressFamily.AF_INET
    assert (
        ip_lookup_config.ip_stack_config(undiscoverable) is ip_lookup.IPStackConfig.IPv4
    )  # That's strange
    assert (
        ip_address_of(
            undiscoverable,
            socket.AddressFamily.AF_INET,
        )
        == _FALLBACK_ADDRESS_IPV4
    )
    assert (
        ip_address_of(
            undiscoverable,
            socket.AddressFamily.AF_INET6,
        )
        == _FALLBACK_ADDRESS_IPV6
    )


def test_cached_dns_lookup_is_config_cached_ok(monkeypatch: MonkeyPatch) -> None:
    patch_config_cache(
        monkeypatch, {(HostName("config_cached_host"), socket.AF_INET): HostAddress("1.2.3.4")}
    )
    patch_persisted_cache(
        monkeypatch, {(HostName("config_cached_host"), socket.AF_INET): HostAddress("6.6.6.6")}
    )
    patch_actual_lookup(
        monkeypatch, {(HostName("config_cached_host"), socket.AF_INET): HostAddress("7.7.7.7")}
    )

    assert ip_lookup.cached_dns_lookup(
        HostName("config_cached_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == HostAddress("1.2.3.4")
    assert ip_lookup.cached_dns_lookup(
        HostName("config_cached_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == HostAddress("1.2.3.4")


def test_cached_dns_lookup_reraises(monkeypatch: MonkeyPatch) -> None:
    patch_config_cache(
        monkeypatch,
        {
            (HostName("the_host_that_raised"), socket.AF_INET6): MKIPAddressLookupError(),
        },
    )
    patch_persisted_cache(monkeypatch, {})
    patch_actual_lookup(monkeypatch, {})

    with pytest.raises(MKIPAddressLookupError):
        _ = ip_lookup.cached_dns_lookup(
            HostName("the_host_that_raised"),
            family=socket.AF_INET6,
            force_file_cache_renewal=False,
        )

    with pytest.raises(MKIPAddressLookupError):
        _ = ip_lookup.cached_dns_lookup(
            HostName("the_host_that_raised"),
            family=socket.AF_INET6,
            force_file_cache_renewal=True,
        )


def test_cached_dns_lookup_is_persisted_cached_ok(monkeypatch: MonkeyPatch) -> None:
    config_ipcache: _IPLookupCacheMapping = {}
    persisted_cache: _PersistedCache = {
        (HostName("persisted_cached_host"), socket.AF_INET): HostAddress("1.2.3.4")
    }

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(
        monkeypatch, {(HostName("persisted_cached_host"), socket.AF_INET): HostAddress("6.6.6.6")}
    )

    assert ip_lookup.cached_dns_lookup(
        HostName("persisted_cached_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == HostAddress("1.2.3.4")
    assert config_ipcache.pop((HostName("persisted_cached_host"), socket.AF_INET)) == HostAddress(
        "1.2.3.4"
    )
    assert persisted_cache[(HostName("persisted_cached_host"), socket.AF_INET)] == HostAddress(
        "1.2.3.4"
    )

    assert ip_lookup.cached_dns_lookup(
        HostName("persisted_cached_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == HostAddress("6.6.6.6")
    assert config_ipcache[(HostName("persisted_cached_host"), socket.AF_INET)] == HostAddress(
        "6.6.6.6"
    )
    assert persisted_cache[(HostName("persisted_cached_host"), socket.AF_INET)] == HostAddress(
        "6.6.6.6"
    )


def test_cached_dns_lookup_is_persisted_cached_ok_unchanged(monkeypatch: MonkeyPatch) -> None:
    config_ipcache: _IPLookupCacheMapping = {}
    persisted_cache: _PersistedCache = {
        (HostName("persisted_cached_host"), socket.AF_INET): HostAddress("1.2.3.4")
    }

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(
        monkeypatch, {(HostName("persisted_cached_host"), socket.AF_INET): HostAddress("1.2.3.4")}
    )

    assert ip_lookup.cached_dns_lookup(
        HostName("persisted_cached_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == HostAddress("1.2.3.4")
    assert config_ipcache.pop((HostName("persisted_cached_host"), socket.AF_INET)) == HostAddress(
        "1.2.3.4"
    )
    assert persisted_cache[(HostName("persisted_cached_host"), socket.AF_INET)] == HostAddress(
        "1.2.3.4"
    )

    assert ip_lookup.cached_dns_lookup(
        HostName("persisted_cached_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == HostAddress("1.2.3.4")
    assert config_ipcache.pop((HostName("persisted_cached_host"), socket.AF_INET)) == HostAddress(
        "1.2.3.4"
    )
    assert persisted_cache[(HostName("persisted_cached_host"), socket.AF_INET)] == HostAddress(
        "1.2.3.4"
    )


def test_cached_dns_lookup_uncached(monkeypatch: MonkeyPatch) -> None:
    config_ipcache: _IPLookupCacheMapping = {}
    persisted_cache: _PersistedCache = {}

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(
        monkeypatch, {(HostName("test_host"), socket.AF_INET): HostAddress("3.1.4.1")}
    )

    assert ip_lookup.cached_dns_lookup(
        HostName("test_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == HostAddress("3.1.4.1")
    assert config_ipcache.pop((HostName("test_host"), socket.AF_INET)) == HostAddress("3.1.4.1")
    assert persisted_cache.pop((HostName("test_host"), socket.AF_INET)) == HostAddress("3.1.4.1")

    assert ip_lookup.cached_dns_lookup(
        HostName("test_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == HostAddress("3.1.4.1")
    assert config_ipcache[(HostName("test_host"), socket.AF_INET)] == HostAddress("3.1.4.1")
    assert persisted_cache[(HostName("test_host"), socket.AF_INET)] == HostAddress("3.1.4.1")


def test_cached_dns_lookup_raises_every_time(monkeypatch: MonkeyPatch) -> None:
    config_ipcache: _IPLookupCacheMapping = {}
    persisted_cache: _PersistedCache = {}

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(monkeypatch, {})

    with pytest.raises(MKIPAddressLookupError):
        _ = ip_lookup.cached_dns_lookup(
            HostName("test_host"),
            family=socket.AF_INET,
            force_file_cache_renewal=False,
        )

    with pytest.raises(MKIPAddressLookupError):
        _ = ip_lookup.cached_dns_lookup(
            HostName("test_host"),
            family=socket.AF_INET,
            force_file_cache_renewal=False,
        )


def test_filecache_beats_failing_lookup(monkeypatch: MonkeyPatch) -> None:
    config_ipcache: _IPLookupCacheMapping = {}
    persisted_cache: _PersistedCache = {
        (HostName("test_host"), socket.AF_INET): HostAddress("3.1.4.1")
    }

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(monkeypatch, {})

    assert ip_lookup.cached_dns_lookup(
        HostName("test_host"),
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == HostAddress("3.1.4.1")
    assert persisted_cache[(HostName("test_host"), socket.AF_INET)]


class TestIPLookupCacheSerialzer:
    def test_simple_cache(self) -> None:
        s = ip_lookup.IPLookupCacheSerializer()
        cache_data: Mapping[tuple[HostName | HostAddress, socket.AddressFamily], HostAddress] = {
            (HostName("host1"), socket.AF_INET): HostAddress("1")
        }
        assert s.deserialize(s.serialize(cache_data)) == cache_data


class TestIPLookupCache:
    def test_repr(self) -> None:
        assert isinstance(repr(ip_lookup.IPLookupCache({})), str)

    def test_load_invalid_syntax(self, tmp_path: Path) -> None:
        with ip_lookup.IPLookupCache.PATH.open(mode="w", encoding="utf-8") as f:
            f.write("{...")

        cache = ip_lookup.IPLookupCache({})
        with pytest.raises(SyntaxError):
            cache.load_persisted()
        assert not cache

    def test_update_empty_file(self, tmp_path: Path) -> None:
        cache_id = HostName("host1"), socket.AF_INET
        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache[cache_id] = HostAddress("127.0.0.1")

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id] == HostAddress("127.0.0.1")

    def test_update_existing_file(self, tmp_path: Path) -> None:
        cache_id1 = HostName("host1"), socket.AF_INET
        cache_id2 = HostName("host2"), socket.AF_INET

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache[cache_id1] = HostAddress("127.0.0.1")
        ip_lookup_cache[cache_id2] = HostAddress("127.0.0.2")

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id1] == HostAddress("127.0.0.1")
        assert new_cache_instance[cache_id2] == HostAddress("127.0.0.2")

    def test_update_existing_entry(self, tmp_path: Path) -> None:
        cache_id1 = HostName("host1"), socket.AF_INET
        cache_id2 = HostName("host2"), socket.AF_INET

        ip_lookup_cache = ip_lookup.IPLookupCache(
            {
                cache_id1: HostAddress("1"),
                cache_id2: HostAddress("2"),
            }
        )
        ip_lookup_cache.save_persisted()

        ip_lookup_cache[cache_id1] = HostAddress("127.0.0.1")

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id1] == HostAddress("127.0.0.1")
        assert new_cache_instance[cache_id2] == HostAddress("2")

    def test_update_without_persistence(self, tmp_path: Path) -> None:
        cache_id1 = HostName("host1"), socket.AF_INET

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache[cache_id1] = HostAddress("0.0.0.0")

        with ip_lookup_cache.persisting_disabled():
            ip_lookup_cache[cache_id1] = HostAddress("127.0.0.1")

        assert ip_lookup_cache[cache_id1] == HostAddress("127.0.0.1")

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id1] == HostAddress("0.0.0.0")

    def test_load_legacy(self, tmp_path: Path) -> None:
        cache_id1 = HostName("host1"), socket.AF_INET
        cache_id2 = HostName("host2"), socket.AF_INET

        with ip_lookup.IPLookupCache.PATH.open("w", encoding="utf-8") as f:
            # Using `repr()` to serialize is a **bad** idea.
            f.write(repr({"host1": "127.0.0.1", "host2": "127.0.0.2"}))

        cache = ip_lookup.IPLookupCache({})
        cache.load_persisted()
        assert cache[cache_id1] == HostAddress("127.0.0.1")
        assert cache[cache_id2] == HostAddress("127.0.0.2")

    def test_clear(self, tmp_path: Path) -> None:
        ip_lookup.IPLookupCache(
            {(HostName("host1"), socket.AF_INET): HostAddress("127.0.0.1")}
        ).save_persisted()

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache.load_persisted()
        assert ip_lookup_cache[(HostName("host1"), socket.AF_INET)] == HostAddress("127.0.0.1")

        ip_lookup_cache.clear()

        assert not ip_lookup_cache

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache.load_persisted()
        assert not ip_lookup_cache


def test_update_dns_cache(monkeypatch: MonkeyPatch) -> None:
    def ip_lookup_cache() -> ip_lookup.IPLookupCache:
        cache = ip_lookup.IPLookupCache({})
        cache.load_persisted()
        return cache

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, family=None, socktype=None, proto=None, flags=None: {
            ("blub", socket.AF_INET): [
                (family, None, None, None, (HostAddress("127.0.0.13"), 1337))
            ],
            ("bla", socket.AF_INET): [
                (family, None, None, None, (HostAddress("127.0.0.37"), 1337))
            ],
            ("dual", socket.AF_INET): [
                (family, None, None, None, (HostAddress("127.0.0.42"), 1337))
            ],
        }[(host, family)],
    )

    ts = Scenario()
    ts.add_host(HostName("blub"), tags={TagGroupID("criticality"): TagID("offline")})
    ts.add_host(HostName("bla"))
    ts.add_host(HostName("dual"), tags={TagGroupID("address_family"): TagID("ip-v4v6")})
    config_cache = ts.apply(monkeypatch)
    hosts_config = config_cache.hosts_config
    ip_lookup_config = config_cache.ip_lookup_config()

    assert not ip_lookup_cache()

    result = ip_lookup.update_dns_cache(
        hosts=(
            hn
            for hn in hosts_config.hosts
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        ),
        ip_lookup_config=ip_lookup_config,
    )
    assert ip_lookup_cache() == {
        ("blub", socket.AF_INET): HostAddress("127.0.0.13"),
        ("bla", socket.AF_INET): HostAddress("127.0.0.37"),
        ("dual", socket.AF_INET): HostAddress("127.0.0.42"),
    }
    # Actual failure is:
    # MKIPAddressLookupError("Failed to lookup IPv6 address of dual via DNS: ('dual', <AddressFamily.AF_INET6: 10>)")
    assert result == (3, ["dual"])

    # Check persisted data
    cache = ip_lookup_cache()
    assert cache.get((HostName("blub"), socket.AF_INET)) == HostAddress("127.0.0.13")
    assert cache.get((HostName("blub"), socket.AF_INET6)) is None
    assert cache.get((HostName("bla"), socket.AF_INET)) == HostAddress("127.0.0.37")
    assert cache.get((HostName("bla"), socket.AF_INET6)) is None
    assert cache.get((HostName("dual"), socket.AF_INET)) == HostAddress("127.0.0.42")
    assert cache.get((HostName("dual"), socket.AF_INET6)) is None


@pytest.mark.parametrize(
    "hostname_str, tags, result_address",
    [
        # default IPv4 host
        (HostName("localhost"), {}, HostAddress("127.0.0.1")),
        (HostAddress("127.0.0.1"), {}, HostAddress("127.0.0.1")),
        # explicit IPv4 host
        (
            HostName("localhost"),
            {
                TagGroupID("address_family"): TagID("ip-v4-only"),
            },
            HostAddress("127.0.0.1"),
        ),
        (
            HostAddress("127.0.0.1"),
            {
                TagGroupID("address_family"): TagID("ip-v4-only"),
            },
            HostAddress("127.0.0.1"),
        ),
    ],
)
def test_lookup_mgmt_board_ip_address_ipv4_host(
    monkeypatch: MonkeyPatch, hostname_str: str, tags: dict[TagGroupID, TagID], result_address: str
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags=tags)

    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (
        ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)(
            hostname, ip_lookup_config.default_address_family(hostname)
        )
        == result_address
    )


@pytest.mark.parametrize(
    "hostname_str, result_address",
    [
        ("localhost", "::1"),
        ("::1", "::1"),
    ],
)
def test_lookup_mgmt_board_ip_address_ipv6_host(
    monkeypatch: MonkeyPatch, hostname_str: str, result_address: str
) -> None:
    hostname = HostName(hostname_str)
    ts = Scenario()
    ts.add_host(hostname, tags={TagGroupID("address_family"): TagID("ip-v6-only")})
    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, family=None, socktype=None, proto=None, flags=None: {
            # That looks like a tautological tests.  It's most likely useless.
            (HostName("localhost"), socket.AF_INET6): [
                (family, None, None, None, (result_address, 0))
            ],
            (HostAddress("::1"), socket.AF_INET6): [
                (family, None, None, None, (result_address, 0))
            ],
        }[(host, family)],
    )

    ip_lookup_config = config_cache.ip_lookup_config()
    assert (
        ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)(
            hostname, ip_lookup_config.default_address_family(hostname)
        )
        == result_address
    )


@pytest.mark.parametrize(
    "hostname, result_address",
    [
        (HostName("localhost"), HostAddress("127.0.0.1")),
        (HostAddress("127.0.0.1"), HostAddress("127.0.0.1")),
    ],
)
def test_lookup_mgmt_board_ip_address_dual_host(
    monkeypatch: MonkeyPatch, hostname: HostName | HostAddress, result_address: str
) -> None:
    hostname = HostName(hostname)
    ts = Scenario()
    ts.add_host(
        hostname,
        tags={
            TagGroupID("address_family"): TagID("ip-v4v6"),
        },
    )

    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (
        ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)(
            hostname, ip_lookup_config.default_address_family(hostname)
        )
        == result_address
    )


@pytest.mark.parametrize(
    "tags",
    [
        {},
        {TagGroupID("address_family"): TagID("ip-v4-only")},
        {TagGroupID("address_family"): TagID("ip-v6-only")},
        {TagGroupID("address_family"): TagID("ip-v4v6")},
    ],
)
def test_lookup_mgmt_board_ip_address_unresolvable(
    monkeypatch: MonkeyPatch, tags: dict[TagGroupID, TagID]
) -> None:
    hostname = HostName("unresolveable-hostname")
    ts = Scenario()
    ts.add_host(hostname, tags=tags)

    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (
        ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)(
            hostname, ip_lookup_config.default_address_family(hostname)
        )
        is None
    )


def test_lookup_mgmt_board_ip_address_unresolvable_2(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_lookup_ip_address(*_a, **_kw):
        raise MKIPAddressLookupError("Failed to ...")

    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "_lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(
        config,
        "host_attributes",
        {
            "hostname": {"management_address": "lolo"},
        },
    )

    ip_lookup_config = config_cache.ip_lookup_config()
    assert (
        ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)(
            hostname, ip_lookup_config.default_address_family(hostname)
        )
        is None
    )
