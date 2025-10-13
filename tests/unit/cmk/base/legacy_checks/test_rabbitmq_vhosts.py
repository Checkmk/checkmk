#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.rabbitmq_vhosts import (
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
            [("/", {})],
        ),
    ],
)
def test_discover_rabbitmq_vhosts(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for rabbitmq_vhosts check."""
    parsed = parse_rabbitmq_vhosts(string_table)
    result = list(discover_rabbitmq_vhosts(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
                (0, "Description: Default virtual host"),
                (0, "Total number of messages: 0", [("messages", 0, None, None)]),
                (0, "Ready messages: 0", [("messages_ready", 0, None, None)]),
                (0, "Unacknowledged messages: 0", [("messages_unacknowledged", 0, None, None)]),
                (0, "Published messages: 2", [("message_publish", 2, None, None)]),
                (0, "Rate: 0.0/s", [("message_publish_rate", 0.0, None, None)]),
            ],
        ),
    ],
)
def test_check_rabbitmq_vhosts(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for rabbitmq_vhosts check."""
    parsed = parse_rabbitmq_vhosts(string_table)
    result = list(check_rabbitmq_vhosts(item, params, parsed))
    assert result == expected_results
