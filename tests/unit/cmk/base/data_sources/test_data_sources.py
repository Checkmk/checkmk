#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

import pytest  # type: ignore[import]

# No stub file
from testlib.base import Scenario  # type: ignore[import]

import cmk.utils.piggyback

import cmk.base.config as config
import cmk.base.data_sources.agent as agent
from cmk.base.data_sources import make_sources
from cmk.base.data_sources._data_sources import _make_host_sections
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
    ipaddress = "127.0.0.1"

    assert [type(source) for source in make_sources(host_config, ipaddress)] == sources


def test_piggyback_storage(monkeypatch, mocker):
    hostname = "testhost"
    ipaddress = "1.2.3.4"
    raw_data = b"\n".join((
        b"<<<<piggyback header>>>>",
        b"<<<section>>>",
        b"first line",
        b"second line",
        b"<<<<>>>>",
    ))

    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    source = TCPDataSource(hostname, ipaddress)
    monkeypatch.setattr(time, "time", lambda: 0)
    mhs = agent.Parser(logging.getLogger("test")).parse(hostname, raw_data, check_interval=0)
    monkeypatch.setattr(
        type(source),
        "run",
        lambda self, *, selected_sections: mhs,
    )

    mocker.patch.object(
        cmk.utils.piggyback,
        "store_piggyback_raw_data",
        autospec=True,
    )

    # End of setup

    _make_host_sections(
        [(hostname, ipaddress, [source])],
        max_cachefile_age=0,
        selected_sections=None,
    )

    args = cmk.utils.piggyback.store_piggyback_raw_data.call_args.args  # type: ignore[attr-defined]

    assert mhs.piggybacked_raw_data
    assert args == (hostname, mhs.piggybacked_raw_data)
