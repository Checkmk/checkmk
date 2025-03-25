#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.plugins import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins

from cmk.agent_based.v2 import Metric, Result, State

SECTION = [
    ["up1", "2"],
    ["up2", "2"],
    ["up3", "2"],
    ["down1", "1"],
    ["down2", "1"],
    ["down3", "1"],
]


@pytest.mark.parametrize(
    "tunnels_ignore_levels, expected_check_result",
    [
        pytest.param(
            [],
            [
                Result(state=State.OK, summary="Total: 6, Up: 3, Down: 3, Ignored: 0"),
                Metric("active_vpn_tunnels", 3.0, boundaries=(0.0, 6.0)),
                Result(
                    state=State.OK,
                    summary="4 additional details available",
                    details="Down and not ignored:\ndown1, down2, down3\nDown:\ndown1, down2, down3",
                ),
            ],
            id="empty ignore",
        ),
        pytest.param(
            ["up2"],
            [
                Result(state=State.OK, summary="Total: 6, Up: 3, Down: 3, Ignored: 0"),
                Metric("active_vpn_tunnels", 3.0, boundaries=(0.0, 6.0)),
                Result(
                    state=State.OK,
                    summary="4 additional details available",
                    details="Down and not ignored:\ndown1, down2, down3\nDown:\ndown1, down2, down3",
                ),
            ],
            id="ignore up2",
        ),
        pytest.param(
            ["down2"],
            [
                Result(state=State.OK, summary="Total: 6, Up: 3, Down: 3, Ignored: 1"),
                Metric("active_vpn_tunnels", 3.0, boundaries=(0.0, 6.0)),
                Result(
                    state=State.OK,
                    summary="6 additional details available",
                    details="Down and not ignored:\ndown1, down3\nDown:\ndown1, down2, down3\nIgnored:\ndown2",
                ),
            ],
            id="ignore down2",
        ),
        pytest.param(
            ["down2", "up2"],
            [
                Result(state=State.OK, summary="Total: 6, Up: 3, Down: 3, Ignored: 1"),
                Metric("active_vpn_tunnels", 3.0, boundaries=(0.0, 6.0)),
                Result(
                    state=State.OK,
                    summary="6 additional details available",
                    details="Down and not ignored:\ndown1, down3\nDown:\ndown1, down2, down3\nIgnored:\ndown2",
                ),
            ],
            id="ignore down2 and up2",
        ),
    ],
)
def test_fortigate_ipsecvpn_simple(
    agent_based_plugins: AgentBasedPlugins,
    tunnels_ignore_levels: list[str],
    expected_check_result: list[Result | Metric],
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("fortigate_ipsecvpn")]
    assert plugin
    assert (
        list(
            plugin.check_function(
                params={"levels": (10, 20), "tunnels_ignore_levels": tunnels_ignore_levels},
                item=None,
                section=SECTION,
            )
        )
        == expected_check_result
    )
