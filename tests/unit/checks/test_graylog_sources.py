#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import get_value_store, Metric, Result, State
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPlugin, CheckPluginName
from cmk.utils.sectionname import SectionName


@pytest.fixture(name="check")
def _graylog_sources_check_plugin(agent_based_plugins: AgentBasedPlugins) -> CheckPlugin:
    return agent_based_plugins.check_plugins[CheckPluginName("graylog_sources")]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "section, item, expected_check_result",
    [
        pytest.param(
            [['{"sources": {"172.18.0.1": {"messages": 457, "has_since_argument": false}}}']],
            "not_found",
            [],
            id="If the item is not found, there are no results.",
        ),
        pytest.param(
            [['{"sources": {"172.18.0.1": {"messages": 457, "has_since_argument": false}}}']],
            "172.18.0.1",
            [
                Result(state=State.OK, summary="Total number of messages: 457"),
                Metric("messages", 457.0),
                Result(
                    state=State.OK,
                    summary="Average number of messages (30 minutes 0 seconds): 0.00",
                ),
                Metric("msgs_avg", 0.0),
                Result(
                    state=State.OK,
                    summary="Total number of messages since last check (within 30 minutes 0 seconds): 0",
                ),
                Metric("graylog_diff", 0.0),
            ],
            id="Timeframe for 'source_since' not configured.",
        ),
        pytest.param(
            [
                [
                    '{"sources": {"172.18.0.1": {"messages": 457, "has_since_argument": true, "messages_since": 5, "source_since": 1800}}}'
                ]
            ],
            "172.18.0.1",
            [
                Result(state=State.OK, summary="Total number of messages: 457"),
                Metric("messages", 457.0),
                Result(
                    state=State.OK,
                    summary="Average number of messages (30 minutes 0 seconds): 0.00",
                ),
                Metric("msgs_avg", 0.0),
                Result(
                    state=State.OK,
                    summary="Total number of messages in the last 30 minutes 0 seconds: 5",
                ),
                Metric("graylog_diff", 5.0),
            ],
            id="Timeframe for 'source_since' configured. Now the check gives information about the total number of messages received in the timeframe.",
        ),
    ],
)
def test_check_graylog_sources(
    check: CheckPlugin,
    agent_based_plugins: AgentBasedPlugins,
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result | Metric],
) -> None:
    parse_graylog_sources = agent_based_plugins.agent_sections[
        SectionName("graylog_sources")
    ].parse_function

    get_value_store()["graylog_msgs_avg.rate"] = 1670328674.09963, 457

    assert (
        list(
            check.check_function(
                item=item,
                params={},
                section=parse_graylog_sources(section),
            )
        )
        == expected_check_result
    )
