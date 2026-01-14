#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.rabbitmq_cluster import (
    check_rabbitmq_cluster,
    discover_rabbitmq_cluster,
    parse_rabbitmq_cluster,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    '{"cluster_name": "rabbit@my-rabbit", "message_stats": {"confirm": 0, "confirm_details": {"rate": 0.0}, "disk_reads": 0, "disk_reads_details": {"rate": 0.0}, "disk_writes": 0, "disk_writes_details": {"rate": 0.0}, "drop_unroutable": 0, "drop_unroutable_details": {"rate": 0.0}, "publish": 2, "publish_details": {"rate": 0.0}, "return_unroutable": 0, "return_unroutable_details": {"rate": 0.0}}, "churn_rates": {"channel_closed": 2, "channel_closed_details": {"rate": 0.0}, "channel_created": 2, "channel_created_details": {"rate": 0.0}, "connection_closed": 10, "connection_closed_details": {"rate": 0.0}, "connection_created": 10, "connection_created_details": {"rate": 0.0}, "queue_created": 1, "queue_created_details": {"rate": 0.0}, "queue_declared": 1, "queue_declared_details": {"rate": 0.0}, "queue_deleted": 0, "queue_deleted_details": {"rate": 0.0}}, "queue_totals": {"messages": 2, "messages_details": {"rate": 0.0}, "messages_ready": 2, "messages_ready_details": {"rate": 0.0}, "messages_unacknowledged": 0, "messages_unacknowledged_details": {"rate": 0.0}}, "object_totals": {"channels": 0, "connections": 0, "consumers": 0, "exchanges": 7, "queues": 1}}'
                ]
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_rabbitmq_cluster(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for rabbitmq_cluster check."""
    parsed = parse_rabbitmq_cluster(string_table)
    result = list(discover_rabbitmq_cluster(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [
                    '{"cluster_name": "rabbit@my-rabbit", "message_stats": {"confirm": 0, "confirm_details": {"rate": 0.0}, "disk_reads": 0, "disk_reads_details": {"rate": 0.0}, "disk_writes": 0, "disk_writes_details": {"rate": 0.0}, "drop_unroutable": 0, "drop_unroutable_details": {"rate": 0.0}, "publish": 2, "publish_details": {"rate": 0.0}, "return_unroutable": 0, "return_unroutable_details": {"rate": 0.0}}, "churn_rates": {"channel_closed": 2, "channel_closed_details": {"rate": 0.0}, "channel_created": 2, "channel_created_details": {"rate": 0.0}, "connection_closed": 10, "connection_closed_details": {"rate": 0.0}, "connection_created": 10, "connection_created_details": {"rate": 0.0}, "queue_created": 1, "queue_created_details": {"rate": 0.0}, "queue_declared": 1, "queue_declared_details": {"rate": 0.0}, "queue_deleted": 0, "queue_deleted_details": {"rate": 0.0}}, "queue_totals": {"messages": 2, "messages_details": {"rate": 0.0}, "messages_ready": 2, "messages_ready_details": {"rate": 0.0}, "messages_unacknowledged": 0, "messages_unacknowledged_details": {"rate": 0.0}}, "object_totals": {"channels": 0, "connections": 0, "consumers": 0, "exchanges": 7, "queues": 1}}'
                ]
            ],
            [
                (0, "Cluster name: rabbit@my-rabbit"),
                (0, "Rabbitmq version: None"),
                (0, "Erlang version: None"),
            ],
        ),
    ],
)
def test_check_rabbitmq_cluster(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for rabbitmq_cluster check."""
    parsed = parse_rabbitmq_cluster(string_table)
    result = list(check_rabbitmq_cluster(item, params, parsed))
    assert result == expected_results
