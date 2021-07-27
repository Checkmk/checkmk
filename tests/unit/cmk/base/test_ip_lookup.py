#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Mapping, Optional
import os
import socket

import pytest

from tests.testlib.base import Scenario

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup

_PatchMapping = Mapping[ip_lookup.IPLookupCacheId, Optional[str]]


def patch_config_cache(monkeypatch, cache: _PatchMapping) -> None:
    monkeypatch.setattr(ip_lookup._config_cache, "get", lambda _x: cache)


def patch_persisted_cache(monkeypatch, cache: _PatchMapping) -> None:
    monkeypatch.setattr(ip_lookup, "_get_ip_lookup_cache", lambda: cache)


def patch_actual_lookup(monkeypatch, mapping: _PatchMapping) -> None:
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda hn, _a, fm: [[0, 0, 0, 0, [mapping[(hn, fm)]]]])


def _empty() -> Dict[ip_lookup.IPLookupCacheId, Optional[str]]:  # just centralize type hint...
    return {}


def test_cached_dns_lookup_is_config_cached_ok(monkeypatch):
    patch_config_cache(monkeypatch, {("config_cached_host", socket.AF_INET): "1.2.3.4"})
    patch_persisted_cache(monkeypatch, {("config_cached_host", socket.AF_INET): "6.6.6.6"})
    patch_actual_lookup(monkeypatch, {("config_cached_host", socket.AF_INET): "7.7.7.7"})

    assert ip_lookup.cached_dns_lookup(
        "config_cached_host",
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == "1.2.3.4"
    assert ip_lookup.cached_dns_lookup(
        "config_cached_host",
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == "1.2.3.4"


def test_cached_dns_lookup_is_config_cached_none(monkeypatch):
    patch_config_cache(monkeypatch, {("the_host_that_raised", socket.AF_INET6): None})
    patch_persisted_cache(monkeypatch, _empty())
    patch_actual_lookup(monkeypatch, _empty())

    assert ip_lookup.cached_dns_lookup(
        "the_host_that_raised",
        family=socket.AF_INET6,
        force_file_cache_renewal=False,
    ) is None
    assert ip_lookup.cached_dns_lookup(
        "the_host_that_raised",
        family=socket.AF_INET6,
        force_file_cache_renewal=True,
    ) is None


def test_cached_dns_lookup_is_persisted_cached_ok(monkeypatch):

    config_ipcache = _empty()
    persisted_cache = {("persisted_cached_host", socket.AF_INET): "1.2.3.4"}

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(monkeypatch, {("persisted_cached_host", socket.AF_INET): "6.6.6.6"})

    assert ip_lookup.cached_dns_lookup(
        "persisted_cached_host",
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == "1.2.3.4"
    assert config_ipcache.pop(("persisted_cached_host", socket.AF_INET)) == "1.2.3.4"
    assert persisted_cache[("persisted_cached_host", socket.AF_INET)] == "1.2.3.4"

    assert ip_lookup.cached_dns_lookup(
        "persisted_cached_host",
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == "6.6.6.6"
    assert config_ipcache[("persisted_cached_host", socket.AF_INET)] == "6.6.6.6"
    assert persisted_cache[("persisted_cached_host", socket.AF_INET)] == "6.6.6.6"


def test_cached_dns_lookup_is_persisted_cached_ok_unchanged(monkeypatch):

    config_ipcache = _empty()
    persisted_cache = {("persisted_cached_host", socket.AF_INET): "1.2.3.4"}

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(monkeypatch, {("persisted_cached_host", socket.AF_INET): "1.2.3.4"})

    assert ip_lookup.cached_dns_lookup(
        "persisted_cached_host",
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == "1.2.3.4"
    assert config_ipcache.pop(("persisted_cached_host", socket.AF_INET)) == "1.2.3.4"
    assert persisted_cache[("persisted_cached_host", socket.AF_INET)] == "1.2.3.4"

    assert ip_lookup.cached_dns_lookup(
        "persisted_cached_host",
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == "1.2.3.4"
    assert config_ipcache.pop(("persisted_cached_host", socket.AF_INET)) == "1.2.3.4"
    assert persisted_cache[("persisted_cached_host", socket.AF_INET)] == "1.2.3.4"


def test_cached_dns_lookup_uncached(monkeypatch):

    config_ipcache = _empty()
    persisted_cache = _empty()

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(monkeypatch, {("test_host", socket.AF_INET): "3.1.4.1"})

    assert ip_lookup.cached_dns_lookup(
        "test_host",
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) == "3.1.4.1"
    assert config_ipcache.pop(("test_host", socket.AF_INET)) == "3.1.4.1"
    assert persisted_cache.pop(("test_host", socket.AF_INET)) == "3.1.4.1"

    assert ip_lookup.cached_dns_lookup(
        "test_host",
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == "3.1.4.1"
    assert config_ipcache[("test_host", socket.AF_INET)] == "3.1.4.1"
    assert persisted_cache[("test_host", socket.AF_INET)] == "3.1.4.1"


def test_cached_dns_lookup_raises_once(monkeypatch):

    config_ipcache = _empty()
    persisted_cache = _empty()

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(monkeypatch, {})

    with pytest.raises(ip_lookup.MKIPAddressLookupError):
        _ = ip_lookup.cached_dns_lookup(
            "test_host",
            family=socket.AF_INET,
            force_file_cache_renewal=False,
        )

    assert ip_lookup.cached_dns_lookup(
        "test_host",
        family=socket.AF_INET,
        force_file_cache_renewal=False,
    ) is None
    assert ip_lookup.cached_dns_lookup(
        "test_host",
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) is None


def test_filecache_beats_failing_lookup(monkeypatch):

    config_ipcache = _empty()
    persisted_cache = {("test_host", socket.AF_INET): "3.1.4.1"}

    patch_config_cache(monkeypatch, config_ipcache)
    patch_persisted_cache(monkeypatch, persisted_cache)
    patch_actual_lookup(monkeypatch, {})

    assert ip_lookup.cached_dns_lookup(
        "test_host",
        family=socket.AF_INET,
        force_file_cache_renewal=True,
    ) == "3.1.4.1"
    assert persisted_cache[("test_host", socket.AF_INET)]


# TODO: Can be removed when this is not executed through a symlink anymore.
# tests/unit/cmk/base/conftest.py::clear_config_caches() then cares about this.
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches_ip_lookup(monkeypatch):
    from cmk.utils.caching import (  # pylint: disable=import-outside-toplevel
        config_cache as _config_cache,)
    from cmk.utils.caching import runtime_cache as _runtime_cache
    _config_cache.clear()
    _runtime_cache.clear()


@pytest.fixture(autouse=True, scope="function")
def clear_ip_lookup_cache_file(monkeypatch):
    ip_lookup.IPLookupCache.PATH.unlink(missing_ok=True)


class TestIPLookupCacheSerialzer:
    def test_simple_cache(self):
        s = ip_lookup.IPLookupCacheSerializer()
        cache_data = {("host1", socket.AF_INET): "1"}
        assert s.deserialize(s.serialize(cache_data)) == cache_data


class TestIPLookupCache:
    def test_repr(self):
        assert isinstance(repr(ip_lookup.IPLookupCache({})), str)

    def test_load_invalid_syntax(self, tmp_path):
        with ip_lookup.IPLookupCache.PATH.open(mode="w", encoding="utf-8") as f:
            f.write(u"{...")

        cache = ip_lookup.IPLookupCache({})
        cache.load_persisted()
        assert not cache

    def test_update_empty_file(self, tmp_path):
        cache_id = "host1", socket.AF_INET
        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache[cache_id] = "127.0.0.1"

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id] == "127.0.0.1"

    def test_update_existing_file(self, tmp_path):
        cache_id1 = "host1", socket.AF_INET
        cache_id2 = "host2", socket.AF_INET

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache[cache_id1] = "127.0.0.1"
        ip_lookup_cache[cache_id2] = "127.0.0.2"

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id1] == "127.0.0.1"
        assert new_cache_instance[cache_id2] == "127.0.0.2"

    def test_update_existing_entry(self, tmp_path):
        cache_id1 = "host1", socket.AF_INET
        cache_id2 = "host2", socket.AF_INET

        ip_lookup_cache = ip_lookup.IPLookupCache({
            cache_id1: "1",
            cache_id2: "2",
        })
        ip_lookup_cache.save_persisted()

        ip_lookup_cache[cache_id1] = "127.0.0.1"

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id1] == "127.0.0.1"
        assert new_cache_instance[cache_id2] == "2"

    def test_update_without_persistence(self, tmp_path):
        cache_id1 = "host1", socket.AF_INET

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache[cache_id1] = "0.0.0.0"

        with ip_lookup_cache.persisting_disabled():
            ip_lookup_cache[cache_id1] = "127.0.0.1"

        assert ip_lookup_cache[cache_id1] == "127.0.0.1"

        new_cache_instance = ip_lookup.IPLookupCache({})
        new_cache_instance.load_persisted()
        assert new_cache_instance[cache_id1] == "0.0.0.0"

    def test_load_legacy(self, tmp_path):
        cache_id1 = "host1", socket.AF_INET
        cache_id2 = "host2", socket.AF_INET

        with ip_lookup.IPLookupCache.PATH.open("w", encoding="utf-8") as f:
            f.write(repr({"host1": "127.0.0.1", "host2": "127.0.0.2"}))

        cache = ip_lookup.IPLookupCache({})
        cache.load_persisted()
        assert cache[cache_id1] == "127.0.0.1"
        assert cache[cache_id2] == "127.0.0.2"

    def test_clear(self, tmp_path):
        ip_lookup.IPLookupCache({("host1", socket.AF_INET): "127.0.0.1"}).save_persisted()

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache.load_persisted()
        assert ip_lookup_cache[("host1", socket.AF_INET)] == "127.0.0.1"

        ip_lookup_cache.clear()

        assert not ip_lookup_cache

        ip_lookup_cache = ip_lookup.IPLookupCache({})
        ip_lookup_cache.load_persisted()
        assert not ip_lookup_cache


def test_update_dns_cache(monkeypatch):
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

    config_cache = config.get_config_cache()
    assert ip_lookup.update_dns_cache(
        host_configs=(config_cache.get_host_config(hn) for hn in config_cache.all_active_hosts()),
        configured_ipv4_addresses={},
        configured_ipv6_addresses={},
        simulation_mode=False,
        override_dns=None,
    ) == (3, ["dual"])

    # Check persisted data
    cache = ip_lookup.IPLookupCache({})
    cache.load_persisted()
    assert cache[("blub", socket.AF_INET)] == "127.0.0.13"
    assert cache.get(("dual", socket.AF_INET6)) is None


@pytest.mark.parametrize(
    "hostname, tags, result_address",
    [
        # default IPv4 host
        ("localhost", {}, "127.0.0.1"),
        ("127.0.0.1", {}, "127.0.0.1"),
        # explicit IPv4 host
        ("localhost", {
            "address_family": "ip-v4-only",
        }, "127.0.0.1"),
        ("127.0.0.1", {
            "address_family": "ip-v4-only",
        }, "127.0.0.1"),
    ])
def test_lookup_mgmt_board_ip_address_ipv4_host(monkeypatch, hostname, tags, result_address):
    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.apply(monkeypatch)
    host_config = config.get_config_cache().get_host_config(hostname)
    assert config.lookup_mgmt_board_ip_address(host_config) == result_address


@pytest.mark.parametrize("hostname, result_address", [
    ("localhost", "::1"),
    ("::1", "::1"),
])
def test_lookup_mgmt_board_ip_address_ipv6_host(monkeypatch, hostname, result_address):
    ts = Scenario()
    ts.add_host(hostname, tags={
        "address_family": "ip-v6-only",
    })
    ts.apply(monkeypatch)
    host_config = config.get_config_cache().get_host_config(hostname)
    assert config.lookup_mgmt_board_ip_address(host_config) == result_address


@pytest.mark.parametrize("hostname, result_address", [
    ("localhost", "127.0.0.1"),
    ("127.0.0.1", "127.0.0.1"),
])
def test_lookup_mgmt_board_ip_address_dual_host(monkeypatch, hostname, result_address):
    ts = Scenario()
    ts.add_host(hostname, tags={
        "address_family": "ip-v4v6",
    })
    ts.apply(monkeypatch)
    host_config = config.get_config_cache().get_host_config(hostname)
    assert config.lookup_mgmt_board_ip_address(host_config) == result_address


@pytest.mark.parametrize("tags, family", [
    ({}, socket.AF_INET),
    ({
        "address_family": "ip-v4-only",
    }, socket.AF_INET),
    ({
        "address_family": "ip-v6-only",
    }, socket.AF_INET6),
    ({
        "address_family": "ip-v4v6",
    }, socket.AF_INET),
])
def test_lookup_mgmt_board_ip_address_unresolveable(monkeypatch, tags, family):
    hostname = "unresolveable-hostname"
    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.apply(monkeypatch)
    host_config = config.get_config_cache().get_host_config(hostname)
    assert config.lookup_mgmt_board_ip_address(host_config) is None
