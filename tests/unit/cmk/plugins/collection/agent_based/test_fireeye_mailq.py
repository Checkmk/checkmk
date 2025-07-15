#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.utils.sectionname import SectionName

from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckFunction,
    CheckPlugin,
    CheckPluginName,
    DiscoveryFunction,
)

from cmk.agent_based.v2 import Metric, Result, Service, State

_PLUGIN = CheckPluginName("fireeye_mailq")


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[_PLUGIN]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{_PLUGIN}")
def _get_discovery_function(plugin: CheckPlugin) -> DiscoveryFunction:
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{_PLUGIN}")
def _get_check_function(plugin: CheckPlugin) -> CheckFunction:
    return lambda p, s: plugin.check_function(params=p, section=s)


@pytest.fixture(scope="module", name="section")
def _get_section(agent_based_plugins: AgentBasedPlugins) -> object:
    parse_fireeye_mailq = agent_based_plugins.snmp_sections[
        SectionName("fireeye_mailq")
    ].parse_function
    return parse_fireeye_mailq([[["0", "0", "0", "3", "5"]]])


def test_discover_somehting(discover_fireeye_mailq: DiscoveryFunction, section: object) -> None:
    assert list(discover_fireeye_mailq(section)) == [
        Service(),
    ]


def test_check(check_fireeye_mailq: CheckFunction, section: object) -> None:
    params = {
        # deferred not present
        "hold": (1, 5),  # OK case
        "active": (1, 5),  # WARN case
        "drop": (1, 5),  # CRIT case
    }
    assert list(check_fireeye_mailq(params, section)) == [
        Result(state=State.OK, summary="Mails in deferred queue: 0"),
        Metric("mail_queue_deferred_length", 0.0),
        Result(state=State.OK, summary="Mails in hold queue: 0"),
        Metric("mail_queue_hold_length", 0.0, levels=(1.0, 5.0)),
        Result(state=State.OK, summary="Mails in incoming queue: 0"),
        Metric("mail_queue_incoming_length", 0.0),
        Result(state=State.WARN, summary="Mails in active queue: 3 (warn/crit at 1/5)"),
        Metric("mail_queue_active_length", 3.0, levels=(1.0, 5.0)),
        Result(state=State.CRIT, summary="Mails in drop queue: 5 (warn/crit at 1/5)"),
        Metric("mail_queue_drop_length", 5.0, levels=(1.0, 5.0)),
    ]
