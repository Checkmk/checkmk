#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.rabbitmq_vhosts import (
    check_rabbitmq_vhosts,
    discover_rabbitmq_vhosts,
    parse_rabbitmq_vhosts,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"description": "Default virtual host", "message_stats": {"publish": 2, "publish_details": {"rate": 0.0}}, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "/"}'
                ]
            ],
            [Service(item="/")],
        ),
    ],
)
def test_discover_rabbitmq_vhosts(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for rabbitmq_vhosts check."""
    parsed = parse_rabbitmq_vhosts(string_table)
    assert list(discover_rabbitmq_vhosts(parsed)) == expected_discoveries


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "/",
            {},
            [
                [
                    '{"description": "Default virtual host", "message_stats": {"publish": 2, "publish_details": {"rate": 0.0}}, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "/"}'
                ]
            ],
            [
                Result(state=State.OK, summary="Description: Default virtual host"),
                Result(state=State.OK, summary="Total number of messages: 0"),
                Metric("messages", 0),
                Result(state=State.OK, summary="Ready messages: 0"),
                Metric("messages_ready", 0),
                Result(state=State.OK, summary="Unacknowledged messages: 0"),
                Metric("messages_unacknowledged", 0),
                Result(state=State.OK, summary="Published messages: 2"),
                Metric("message_publish", 2),
                Result(state=State.OK, summary="Rate: 0.0/s"),
                Metric("message_publish_rate", 0.0),
            ],
        ),
    ],
)
def test_check_rabbitmq_vhosts(
    item: str,
    params: Mapping[str, object],
    string_table: StringTable,
    expected_results: Sequence[object],
) -> None:
    """Test check function for rabbitmq_vhosts check."""
    parsed = parse_rabbitmq_vhosts(string_table)
    assert list(check_rabbitmq_vhosts(item, params, parsed)) == expected_results
