#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import socket
from pathlib import Path

import pytest  # type: ignore[import]

# No stub file
from testlib.base import Scenario  # type: ignore[import]

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup


# TODO: Can be removed when this is not executed through a symlink anymore.
# tests/unit/cmk/base/conftest.py::clear_config_caches() then cares about this.
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches_ip_lookup(monkeypatch):
    from cmk.utils.caching import (  # pylint: disable=import-outside-toplevel
        config_cache as _config_cache,)
    from cmk.utils.caching import runtime_cache as _runtime_cache
    _config_cache.reset()
    _runtime_cache.reset()


@pytest.fixture()
def _cache_file():
    p = Path(ip_lookup._cache_path())
    p.parent.mkdir(parents=True, exist_ok=True)

    yield p

    if p.exists():
        p.unlink()


def test_repr():
    ip_lookup_cache = ip_lookup._get_ip_lookup_cache()
    assert isinstance(repr(ip_lookup_cache), str)


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

    ip_lookup_cache.clear()

    assert len(ip_lookup_cache) == 0
    assert not _cache_file.exists()


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
    assert ip_lookup.lookup_mgmt_board_ip_address(host_config) == result_address


@pytest.mark.skipif(
    os.environ.get('TRAVIS') == 'true',
    reason="Travis may not resolve localhost -> IPv6 (https://github.com/njh/travis-ipv6-test)")
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
    assert ip_lookup.lookup_mgmt_board_ip_address(host_config) == result_address


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
    assert ip_lookup.lookup_mgmt_board_ip_address(host_config) == result_address


@pytest.mark.parametrize("tags, family", [
    ({}, 4),
    ({
        "address_family": "ip-v4-only",
    }, 4),
    ({
        "address_family": "ip-v6-only",
    }, 6),
    ({
        "address_family": "ip-v4v6",
    }, 4),
])
def test_lookup_mgmt_board_ip_address_unresolveable(monkeypatch, tags, family):
    hostname = "unresolveable-hostname"
    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.apply(monkeypatch)
    host_config = config.get_config_cache().get_host_config(hostname)
    assert ip_lookup.lookup_mgmt_board_ip_address(host_config) is None
