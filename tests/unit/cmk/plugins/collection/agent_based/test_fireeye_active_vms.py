#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable

import pytest

from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckFunction,
    CheckPlugin,
    CheckPluginName,
)

from cmk.agent_based.v2 import DiscoveryResult, Metric, Result, Service, State, StringTable

type DiscoveryFunction = Callable[..., DiscoveryResult]

_PLUGIN = CheckPluginName("fireeye_active_vms")


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
def _get_section() -> StringTable:
    return [["42"]]


def test_discover_nothing(discover_fireeye_active_vms: DiscoveryFunction) -> None:
    assert not list(discover_fireeye_active_vms([]))


def test_discover_somehting(
    discover_fireeye_active_vms: DiscoveryFunction, section: StringTable
) -> None:
    assert list(discover_fireeye_active_vms(section)) == [Service()]


def test_check_ok(check_fireeye_active_vms: CheckFunction, section: StringTable) -> None:
    assert list(check_fireeye_active_vms({"vms": (50, 100)}, section)) == [
        Result(state=State.OK, summary="Active VMs: 42"),
        Metric("active_vms", 42.0, levels=(50.0, 100.0)),
    ]


def test_check_warn(check_fireeye_active_vms: CheckFunction, section: StringTable) -> None:
    assert list(check_fireeye_active_vms({"vms": (23, 50)}, section)) == [
        Result(state=State.WARN, summary="Active VMs: 42 (warn/crit at 23/50)"),
        Metric("active_vms", 42.0, levels=(23.0, 50.0)),
    ]


def test_check_crit(check_fireeye_active_vms: CheckFunction, section: StringTable) -> None:
    assert list(check_fireeye_active_vms({"vms": (23, 36)}, section)) == [
        Result(state=State.CRIT, summary="Active VMs: 42 (warn/crit at 23/36)"),
        Metric("active_vms", 42.0, levels=(23.0, 36.0)),
    ]
