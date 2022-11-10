#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import PiggybackFetcher, ProgramFetcher, SNMPFetcher, TCPFetcher

from cmk.base.sources import make_non_cluster_sources


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
):
    ts = make_scenario(hostname, tags)
    ts.apply(monkeypatch)

    assert [
        type(fetcher)
        for _meta, _file_cache, fetcher in make_non_cluster_sources(
            hostname,
            "127.0.0.1",
            simulation_mode=True,
            missing_sys_description=False,
            file_cache_max_age=file_cache.MaxAge.none(),
        )
    ] == sources
