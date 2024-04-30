#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.testlib.base import Scenario

from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.tags import TagGroupID, TagID

from cmk.fetchers import PiggybackFetcher, ProgramFetcher, SNMPFetcher, TCPFetcher, TLSConfig
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.base.config import ConfigCache
from cmk.base.ip_lookup import IPStackConfig
from cmk.base.sources import make_sources, Source


def _make_sources(
    hostname: HostName,
    config_cache: ConfigCache,
    *,
    tmp_path: Path,
) -> Sequence[Source]:
    # Too many arguments to this function.  Let's wrap it to make it easier
    # to test.
    return make_sources(
        hostname,
        HostAddress("127.0.0.1"),
        IPStackConfig.IPv4,
        config_cache=config_cache,
        is_cluster=False,
        simulation_mode=True,
        file_cache_options=FileCacheOptions(),
        file_cache_max_age=MaxAge.zero(),
        snmp_backend_override=None,
        oid_cache_dir=tmp_path,
        stored_walk_path=tmp_path,
        walk_cache_path=tmp_path,
        file_cache_path=tmp_path,
        tcp_cache_path=tmp_path,
        tls_config=TLSConfig(
            cas_dir=tmp_path,
            ca_store=tmp_path,
            site_crt=tmp_path,
        ),
        password_store_file=Path("/pw/store"),
        passwords={},
    )


@pytest.mark.usefixtures("fix_register")
def test_ping_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("ping-host")
    tags = {TagGroupID("agent"): TagID("no-agent")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [PiggybackFetcher]


@pytest.mark.usefixtures("fix_register")
def test_agent_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("agent-host")

    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [TCPFetcher, PiggybackFetcher]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize("snmp_ds", (TagID("snmp-v1"), TagID("snmp-v2")))
def test_snmp_host(snmp_ds: TagID, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("snmp-host")
    tags = {TagGroupID("agent"): TagID("no-agent"), TagGroupID("snmp_ds"): snmp_ds}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [SNMPFetcher, PiggybackFetcher]


@pytest.mark.usefixtures("fix_register")
def test_dual_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("dual-host")
    tags = {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v2")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [TCPFetcher, SNMPFetcher, PiggybackFetcher]


@pytest.mark.usefixtures("fix_register")
def test_all_agents_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("all-agents-host")
    tags = {TagGroupID("agent"): TagID("all-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.set_ruleset(
        "datasource_programs",
        [
            {
                "condition": {
                    "host_name": [hostname],
                },
                "id": "01",
                "value": "echo 1",
            },
        ],
    )
    ts.set_option(
        "special_agents",
        {
            "jolokia": [
                {
                    "condition": {
                        "host_name": [hostname],
                    },
                    "id": "02",
                    "value": {},
                },
            ]
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [ProgramFetcher, ProgramFetcher, PiggybackFetcher]


@pytest.mark.usefixtures("fix_register")
def test_special_agents_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("all-special-host")
    tags = {TagGroupID("agent"): TagID("special-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.set_option(
        "special_agents",
        {
            "jolokia": [
                {
                    "condition": {
                        "host_name": [hostname],
                    },
                    "id": "02",
                    "value": {},
                },
            ]
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [ProgramFetcher, PiggybackFetcher]
