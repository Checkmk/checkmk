#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Final

import pytest

from tests.testlib.base import Scenario

from cmk.utils.type_defs import HostName, result, SectionName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import FetcherType
from cmk.core_helpers.config import AgentParserConfig, SNMPParserConfig

from cmk.base import config
from cmk.base.config import HostConfig
from cmk.base.sources import make_non_cluster_sources
from cmk.base.sources.piggyback import PiggybackSource
from cmk.base.sources.programs import DSProgramSource, SpecialAgentSource
from cmk.base.sources.snmp import SNMPSource
from cmk.base.sources.tcp import TCPSource

AGENT_PARSER_CONFIG: Final = AgentParserConfig(
    check_interval=0,
    encoding_fallback="ascii",
    keep_outdated=False,
    translation={},
    agent_simulator=True,
)


SNMP_PARSER_CONFIG: Final = SNMPParserConfig(
    check_intervals={},
    keep_outdated=False,
)


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
        ("agent-host", {}, [TCPSource, PiggybackSource]),
        (
            "ping-host",
            {"agent": "no-agent"},
            [PiggybackSource],
        ),
        (
            "snmp-host",
            {"agent": "no-agent", "snmp_ds": "snmp-v2"},
            [SNMPSource, PiggybackSource],
        ),
        (
            "snmp-host",
            {"agent": "no-agent", "snmp_ds": "snmp-v1"},
            [SNMPSource, PiggybackSource],
        ),
        (
            "dual-host",
            {"agent": "cmk-agent", "snmp_ds": "snmp-v2"},
            [TCPSource, SNMPSource, PiggybackSource],
        ),
        (
            "all-agents-host",
            {"agent": "all-agents"},
            [DSProgramSource, SpecialAgentSource, PiggybackSource],
        ),
        (
            "all-special-host",
            {"agent": "special-agents"},
            [SpecialAgentSource, PiggybackSource],
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

    host_config = HostConfig.make_host_config(hostname)
    ipaddress = "127.0.0.1"

    assert [
        type(c)
        for c in make_non_cluster_sources(
            host_config,
            ipaddress,
            simulation_mode=True,
            missing_sys_description=False,
            file_cache_max_age=file_cache.MaxAge.none(),
            agent_parser_config=AGENT_PARSER_CONFIG,
            snmp_parser_config=SNMP_PARSER_CONFIG,
        )
    ] == sources


@pytest.mark.parametrize(
    "make_source",
    [
        lambda hostname, ipaddress, base_dir: SpecialAgentSource(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PROGRAM,
            id_="special_veryspecial",
            persisted_section_dir=base_dir,
            cache_dir=base_dir,
            simulation_mode=True,
            agent_simulator=True,
            keep_outdated=False,
            translation={},
            encoding_fallback="ascii",
            check_interval=0,
            cmdline="",
            stdin="",
            is_cmc=False,
            file_cache_max_age=file_cache.MaxAge.none(),
        ),
        lambda hostname, ipaddress, base_dir: DSProgramSource(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PROGRAM,
            id_="agent",
            persisted_section_dir=base_dir,
            cache_dir=base_dir,
            simulation_mode=True,
            agent_simulator=True,
            keep_outdated=False,
            translation={},
            encoding_fallback="ascii",
            check_interval=0,
            cmdline="",
            stdin=None,
            is_cmc=False,
            file_cache_max_age=file_cache.MaxAge.none(),
        ),
        lambda hostname, ipaddress, base_dir: PiggybackSource(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.PIGGYBACK,
            id_="piggyback",
            persisted_section_dir=base_dir,
            cache_dir=base_dir,
            simulation_mode=True,
            agent_simulator=True,
            keep_outdated=False,
            translation={},
            encoding_fallback="ascii",
            time_settings=(),
            check_interval=0,
            is_piggyback_host=True,
            file_cache_max_age=file_cache.MaxAge.none(),
        ),
        lambda hostname, ipaddress, base_dir: TCPSource(
            hostname,
            ipaddress,
            source_type=SourceType.HOST,
            fetcher_type=FetcherType.TCP,
            id_="agent",
            persisted_section_dir=base_dir,
            cache_dir=base_dir,
            simulation_mode=True,
            agent_simulator=True,
            keep_outdated=False,
            translation={},
            encoding_fallback="ascii",
            check_interval=0,
            address_family=socket.AF_INET,
            agent_port=0,
            tcp_connect_timeout=0,
            agent_encryption={},
            file_cache_max_age=file_cache.MaxAge.none(),
        ),
    ],
)
def test_data_source_preselected(  # type:ignore[no-untyped-def]
    monkeypatch,
    make_source,
    tmp_path,
) -> None:
    selected_sections = {SectionName("keep")}  # <- this is what we care about

    # a lot of hocus pocus to instantiate a source:
    hostname = HostName("hostname")
    make_scenario(hostname, {}).apply(monkeypatch)
    monkeypatch.setattr(config, "special_agent_info", {None: lambda *a: []})
    source = make_source(
        hostname,
        "127.0.0.1",
        tmp_path,
    )

    parse_result = source.parse(
        result.OK(
            b"<<<dismiss>>>\n"
            b"this is not\n"
            b"a preselected section\n"
            b"<<<keep>>>\n"
            b"but this is!\n"
        ),
        selection=selected_sections,
    )
    assert parse_result.is_ok()

    sections = parse_result.value(None).sections
    assert set(sections) == selected_sections
