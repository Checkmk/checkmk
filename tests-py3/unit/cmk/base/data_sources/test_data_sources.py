#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib.base import Scenario

from cmk.utils.type_defs import SourceType

import cmk.base.config as config
from cmk.base.data_sources import DataSources
from cmk.base.data_sources.piggyback import PiggyBackDataSource
from cmk.base.data_sources.programs import DSProgramDataSource, SpecialAgentDataSource
from cmk.base.data_sources.snmp import SNMPDataSource
from cmk.base.data_sources.tcp import TCPDataSource


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
    ("agent-host", {}, [TCPDataSource, PiggyBackDataSource]),
    ("ping-host", {
        "agent": "no-agent"
    }, [PiggyBackDataSource]),
    ("snmp-host", {
        "agent": "no-agent",
        "snmp_ds": "snmp-v2"
    }, [SNMPDataSource, PiggyBackDataSource]),
    ("snmp-host", {
        "agent": "no-agent",
        "snmp_ds": "snmp-v1"
    }, [SNMPDataSource, PiggyBackDataSource]),
    ("dual-host", {
        "agent": "cmk-agent",
        "snmp_ds": "snmp-v2"
    }, [TCPDataSource, SNMPDataSource, PiggyBackDataSource]),
    ("all-agents-host", {
        "agent": "all-agents"
    }, [DSProgramDataSource, SpecialAgentDataSource, PiggyBackDataSource]),
    ("all-special-host", {
        "agent": "special-agents"
    }, [SpecialAgentDataSource, PiggyBackDataSource]),
])
def test_get_sources(monkeypatch, hostname, tags, sources):
    ts = make_scenario(hostname, tags)
    ts.apply(monkeypatch)

    host_config = config.HostConfig.make_host_config(hostname)

    assert [s.__class__ for s in DataSources(host_config, "127.0.0.1").get_data_sources()
           ] == sources


def test_get_host_sections(monkeypatch):
    hostname = "testhost"
    address = "1.2.3.4"
    tags = {"agent": "no-agent"}
    make_scenario(hostname, tags).apply(monkeypatch)
    host_config = config.HostConfig.make_host_config(hostname)

    sources = DataSources(host_config, address)
    multi_host_sections = sources.get_host_sections()
    data = multi_host_sections._multi_host_sections
    assert len(data) == 1

    key = (hostname, address, SourceType.HOST)
    assert key in data
    section = data[key]
    assert not section.sections
    assert not section.cache_info
    assert not section.piggybacked_raw_data
    assert not section.persisted_sections
