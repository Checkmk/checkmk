#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.data_sources import DataSources
from testlib.base import Scenario


@pytest.mark.parametrize("hostname,settings", [
    ("agent-host", {
        "tags": {},
        "sources": ['TCPDataSource', 'PiggyBackDataSource'],
    }),
    ("ping-host", {
        "tags": {
            "agent": "no-agent"
        },
        "sources": ['PiggyBackDataSource'],
    }),
    ("snmp-host", {
        "tags": {
            "agent": "no-agent",
            "snmp_ds": "snmp-v2"
        },
        "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
    }),
    ("snmpv1-host", {
        "tags": {
            "agent": "no-agent",
            "snmp_ds": "snmp-v1"
        },
        "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
    }),
    ("dual-host", {
        "tags": {
            "agent": "cmk-agent",
            "snmp_ds": "snmp-v2"
        },
        "sources": ['TCPDataSource', 'SNMPDataSource', 'PiggyBackDataSource'],
    }),
    ("all-agents-host", {
        "tags": {
            "agent": "all-agents"
        },
        "sources": ['DSProgramDataSource', 'SpecialAgentDataSource', 'PiggyBackDataSource'],
    }),
    ("all-special-host", {
        "tags": {
            "agent": "special-agents"
        },
        "sources": ['SpecialAgentDataSource', 'PiggyBackDataSource'],
    }),
])
def test_data_sources_of_hosts(monkeypatch, hostname, settings):
    ts = Scenario().add_host(hostname, tags=settings["tags"])
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
    ts.apply(monkeypatch)

    sources = DataSources(hostname, "127.0.0.1")
    source_names = [s.__class__.__name__ for s in sources.get_data_sources()]
    assert settings["sources"] == source_names, "Wrong sources for %s" % hostname
