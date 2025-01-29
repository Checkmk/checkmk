#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import CheckFunction, CheckPlugin, DiscoveryFunction
from cmk.base.api.agent_based.register import AgentBasedPlugins

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

check_name = "fast_lta_headunit_replication"


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin: CheckPlugin) -> DiscoveryFunction:
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin: CheckPlugin) -> CheckFunction:
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


@pytest.mark.parametrize("info, expected", [([[["60", "1", "1"]]], [Service()])])
def test_discovery_fast_lta_headunit_replication(
    discover_fast_lta_headunit_replication: DiscoveryFunction,
    info: Sequence[StringTable],
    expected: DiscoveryResult,
) -> None:
    assert list(discover_fast_lta_headunit_replication(info)) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            [[["60", "1", "1"]]],
            [Result(state=State.OK, summary="Replication is running. This node is Master.")],
        ),
        (
            [[["60", "1", "99"]]],
            [
                Result(
                    state=State.CRIT,
                    summary="Replication is not running (!!). This node is Master.",
                )
            ],
        ),
        (
            [[["60", "255", "99"]]],
            [
                Result(
                    state=State.CRIT,
                    summary="Replication is not running (!!). This node is standalone.",
                )
            ],
        ),
        (
            [[["60", "88", "99"]]],
            [
                Result(
                    state=State.CRIT,
                    summary="Replication is not running (!!). Replication mode of this node is 88.",
                )
            ],
        ),
    ],
)
def test_check_fast_lta_headunit_replication(
    check_fast_lta_headunit_replication: CheckFunction,
    info: Sequence[StringTable],
    expected: CheckResult,
) -> None:
    assert list(check_fast_lta_headunit_replication(None, {}, info)) == expected
