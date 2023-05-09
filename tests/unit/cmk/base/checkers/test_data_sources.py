#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

# No stub file
from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import result, SectionName

from cmk.base import config
from cmk.base.checkers import make_sources, Mode
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


@pytest.mark.usefixtures("config_load_all_checks")
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


@pytest.mark.parametrize("source, kwargs", [
    (SpecialAgentSource, {
        "special_agent_id": None,
        "params": None
    }),
    (DSProgramSource, {
        "template": ""
    }),
    (PiggybackSource, {}),
    (TCPSource, {}),
])
def test_data_source_preselected(monkeypatch, source, kwargs):

    selected_sections = {SectionName("keep")}  # <- this is what we care about

    # a lot of hocus pocus to instantiate a source:
    make_scenario("hostname", {}).apply(monkeypatch)
    monkeypatch.setattr(config, "special_agent_info", {None: lambda *a: []})
    source_inst = source(
        "hostname",
        "127.0.0.1",
        mode=None,
        **kwargs,
    )

    parse_result = source_inst.parse(
        result.OK(b"<<<dismiss>>>\n"
                  b"this is not\n"
                  b"a preselected section\n"
                  b"<<<keep>>>\n"
                  b"but this is!\n"),
        selection=selected_sections,
    )
    assert parse_result.is_ok()

    sections = parse_result.value(None).sections
    assert set(sections) == selected_sections
