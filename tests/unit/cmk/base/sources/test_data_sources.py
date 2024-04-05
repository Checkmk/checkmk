#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.utils.hostaddress import HostAddress

from cmk.fetchers import PiggybackFetcher, ProgramFetcher, SNMPFetcher, TCPFetcher
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.base.ip_lookup import IPStackConfig
from cmk.base.sources import make_sources


def make_scenario(hostname, tags):
    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.set_ruleset(
        "datasource_programs",
        [
            {
                "condition": {
                    "host_name": ["ds-host-14", "all-agents-host", "all-special-host"],
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
                        "host_name": [
                            "special-host-14",
                            "all-agents-host",
                            "all-special-host",
                        ],
                    },
                    "id": "02",
                    "value": {},
                },
            ]
        },
    )
    return ts


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "hostname, tags, sources",
    [
        ("agent-host", {}, [TCPFetcher, PiggybackFetcher]),
        (
            "ping-host",
            {"agent": "no-agent"},
            [PiggybackFetcher],
        ),
        (
            "snmp-host",
            {"agent": "no-agent", "snmp_ds": "snmp-v2"},
            [SNMPFetcher, PiggybackFetcher],
        ),
        (
            "snmp-host",
            {"agent": "no-agent", "snmp_ds": "snmp-v1"},
            [SNMPFetcher, PiggybackFetcher],
        ),
        (
            "dual-host",
            {"agent": "cmk-agent", "snmp_ds": "snmp-v2"},
            [TCPFetcher, SNMPFetcher, PiggybackFetcher],
        ),
        (
            "all-agents-host",
            {"agent": "all-agents"},
            [ProgramFetcher, ProgramFetcher, PiggybackFetcher],
        ),
        (
            "all-special-host",
            {"agent": "special-agents"},
            [ProgramFetcher, PiggybackFetcher],
        ),
    ],
)
def test_host_config_creates_passing_source_sources(
    monkeypatch,
    hostname,
    tags,
    sources,
    tmp_path,
):
    ts = make_scenario(hostname, tags)
    config_cache = ts.apply(monkeypatch)

    assert [
        type(source.fetcher())
        for source in make_sources(
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
            cas_dir=tmp_path,
            ca_store=tmp_path,
            site_crt=tmp_path,
        )
    ] == sources
