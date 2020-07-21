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
from cmk.utils.type_defs import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.data_sources.agent as agent

from cmk.base import check_table, config
from cmk.base.api.agent_based.type_defs import CheckPlugin
from cmk.base.api.agent_based.register import section_plugins
from cmk.base.api.agent_based.type_defs import CheckPlugin
from cmk.base.api.agent_based.utils import parse_to_string_table
from cmk.base.data_sources import make_sources
from cmk.base.data_sources._data_sources import _make_host_sections, _make_piggybacked_sections
from cmk.base.data_sources.piggyback import PiggyBackDataSource
from cmk.base.data_sources.programs import ProgramDataSource
from cmk.base.data_sources.snmp import SNMPDataSource
from cmk.base.data_sources.tcp import TCPConfigurator, TCPDataSource


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
    }, [ProgramDataSource, ProgramDataSource, PiggyBackDataSource]),
    ("all-special-host", {
        "agent": "special-agents"
    }, [ProgramDataSource, PiggyBackDataSource]),
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

    source = TCPDataSource(configurator=TCPConfigurator(hostname, ipaddress),)
    monkeypatch.setattr(time, "time", lambda: 0)
    mhs = agent.Parser(logging.getLogger("test")).parse(hostname, raw_data, check_interval=0)
    monkeypatch.setattr(
        type(source),
        "run",
        lambda self, *, selected_raw_sections: mhs,
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
        selected_raw_sections=None,
    )

    args = cmk.utils.piggyback.store_piggyback_raw_data.call_args.args  # type: ignore[attr-defined]

    assert mhs.piggybacked_raw_data
    assert args == (hostname, mhs.piggybacked_raw_data)


@pytest.fixture(name="agent_section")
def agent_section_fixture(monkeypatch):
    section = section_plugins.create_agent_section_plugin(
        name="unit_test_agent_section",
        parse_function=parse_to_string_table,
    )
    monkeypatch.setitem(
        config.registered_agent_sections,
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
        remove_duplicates=False,
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
