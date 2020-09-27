#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

# No stub file
from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base import check_table, config
from cmk.base.api.agent_based.register import section_plugins
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.checkers import make_sources, Mode
from cmk.base.checkers._checkers import _make_piggybacked_sections
from cmk.base.checkers.piggyback import PiggybackSource
from cmk.base.checkers.programs import DSProgramSource, SpecialAgentSource
from cmk.base.checkers.snmp import SNMPSource
from cmk.base.checkers.tcp import TCPSource


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


def make_scenario(hostname, tags):
    ts = Scenario().add_host(hostname, tags=tags)
    ts.set_ruleset("datasource_programs", [
        ('echo 1', [], ['ds-host-14', 'all-agents-host', 'all-special-host'], {}),
    ])
    ts.set_option(
        "special_agents",
        {"jolokia": [({}, [], [
            'special-host-14',
            'all-agents-host',
            'all-special-host',
        ], {}),]})
    return ts


@pytest.mark.parametrize("hostname, tags, sources", [
    ("agent-host", {}, [TCPSource, PiggybackSource]),
    (
        "ping-host",
        {
            "agent": "no-agent"
        },
        [PiggybackSource],
    ),
    (
        "snmp-host",
        {
            "agent": "no-agent",
            "snmp_ds": "snmp-v2"
        },
        [SNMPSource, PiggybackSource],
    ),
    (
        "snmp-host",
        {
            "agent": "no-agent",
            "snmp_ds": "snmp-v1"
        },
        [SNMPSource, PiggybackSource],
    ),
    (
        "dual-host",
        {
            "agent": "cmk-agent",
            "snmp_ds": "snmp-v2"
        },
        [TCPSource, SNMPSource, PiggybackSource],
    ),
    (
        "all-agents-host",
        {
            "agent": "all-agents"
        },
        [DSProgramSource, SpecialAgentSource, PiggybackSource],
    ),
    (
        "all-special-host",
        {
            "agent": "special-agents"
        },
        [SpecialAgentSource, PiggybackSource],
    ),
])
def test_host_config_creates_passing_source_sources(
    monkeypatch,
    hostname,
    mode,
    tags,
    sources,
):
    ts = make_scenario(hostname, tags)
    ts.apply(monkeypatch)

    host_config = config.HostConfig.make_host_config(hostname)
    ipaddress = "127.0.0.1"

    assert [type(c) for c in make_sources(
        host_config,
        ipaddress,
        mode=mode,
    )] == sources


@pytest.fixture(name="agent_section")
def agent_section_fixture(monkeypatch):
    section = section_plugins.create_agent_section_plugin(name="unit_test_agent_section",)
    monkeypatch.setitem(
        agent_based_register._config.registered_agent_sections,
        section.name,
        section,
    )
    yield section


@pytest.fixture(name="check_plugin")
def check_plugin_fixture(monkeypatch, agent_section):
    check_plugin = CheckPlugin(
        CheckPluginName("unit_test_check_plugin"),
        [agent_section.parsed_section_name],
        "Unit Test",
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
        None,  # type: ignore[arg-type]  # irrelevant for test
    )
    monkeypatch.setitem(
        agent_based_register._config.registered_check_plugins,
        check_plugin.name,
        check_plugin,
    )
    yield check_plugin


def test_make_piggybacked_sections(monkeypatch, check_plugin):
    cluster_name = "cluster"
    node_name = "node"

    def get_needed_check_names(
        hostname,
        filter_mode=None,
        skip_ignored=True,
    ):
        if hostname == node_name and filter_mode == 'only_clustered':
            return {check_plugin.name}
        return set()

    monkeypatch.setattr(
        check_table,
        "get_needed_check_names",
        get_needed_check_names,
    )

    Scenario().add_cluster(cluster_name, nodes=[node_name]).apply(monkeypatch)
    host_config = config.HostConfig.make_host_config(cluster_name)
    piggybacked_host_sections = _make_piggybacked_sections(host_config)

    assert len(piggybacked_host_sections) == 1
    # comparing cmk.utils.type_defs.SectionName and cmk.utils.type_defs.ParsedSectionName
    assert str(next(iter(piggybacked_host_sections))) == str(check_plugin.sections[0])
