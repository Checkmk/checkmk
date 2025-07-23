from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, StringTable
from cmk.base.legacy_checks.rabbitmq_queues import (
    check_rabbitmq_queues,
    discover_rabbitmq_queues,
    parse_rabbitmq_queues,
)


@pytest.mark.parametrize(
    ["string_table", "expected"],
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [
                [
                    '{"memory": 68036, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "my_queue", "node": "rabbit@my-rabbit", "state": "stopped", "type": "quorum"}'
                ]
            ],
            [("my_queue", {})],
            id="single_queue",
        ),
    ],
)
def test_discover_rabbitmq_queues(string_table: StringTable, expected: list) -> None:
    parsed = parse_rabbitmq_queues(string_table)
    assert expected == list(discover_rabbitmq_queues(parsed))


@pytest.mark.parametrize(
    ["string_table", "params", "expected"],
    [
        pytest.param(
            [
                [
                    '{ "name": "my_queue", "state": ""}',
                ]
            ],
            {},
            # TODO: test case was added to ensure same functionality as before migration to new API
            # but it should be re-evaluated if this output makes sense. It seems to assume a boolean
            # state, but the possible queue state are "running", "stopped", etc.
            [(2, "Is running: ")],
            id="empty_state",
        ),
        pytest.param(
            [
                [
                    '{"memory": 68036, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "my_queue", "node": "rabbit@my-rabbit", "state": "stopped", "type": "quorum"}',
                ]
            ],
            {},
            [
                (0, "Type: Quorum"),
                (0, "Is running: stopped"),
                (0, "Running on node: rabbit@my-rabbit"),
                (0, "Total number of messages: 0", [("messages", 0, None, None)]),
                (0, "Messages ready: 0", [("messages_ready", 0, None, None)]),
                (0, "Messages unacknowledged: 0", [("messages_unacknowledged", 0, None, None)]),
                (0, "Memory used: 66.4 KiB", [("mem_lnx_total_used", 68036, None, None)]),
            ],
            id="quorum_queue_stopped",
        ),
        pytest.param(
            [
                [
                    '{"memory": 9816, "messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "name": "my_queue", "node": "rabbit@my-rabbit", "state": "stopped", "type": "classic"}',
                ]
            ],
            {},
            [
                (0, "Type: Classic"),
                (0, "Is running: stopped"),
                (0, "Running on node: rabbit@my-rabbit"),
                (0, "Total number of messages: 0", [("messages", 0, None, None)]),
                (0, "Messages ready: 0", [("messages_ready", 0, None, None)]),
                (0, "Messages unacknowledged: 0", [("messages_unacknowledged", 0, None, None)]),
                (0, "Memory used: 9.59 KiB", [("mem_lnx_total_used", 9816, None, None)]),
            ],
            id="classic_queue_stopped",
        ),
        pytest.param(
            [
                [
                    '{"memory": 16780, "message_stats": {"publish": 5, "publish_details": {"rate": 0.15}}, "messages": 5, "messages_ready": 5, "messages_unacknowledged": 5, "name": "my_queue", "node": "rabbit@my-rabbit", "state": "running", "type": "classic"}',
                ]
            ],
            {
                "msg_upper": (1, 10),
                "msg_ready_upper": (1, 10),
                "msg_unack_upper": (1, 10),
                "msg_publish_rate_upper": (0.1, 0.5),
                "abs_memory": (10240, 51200),
            },
            [
                (0, "Type: Classic"),
                (0, "Is running: running"),
                (0, "Running on node: rabbit@my-rabbit"),
                (1, "Total number of messages: 5 (warn/crit at 1/10)", [("messages", 5, 1, 10)]),
                (1, "Messages ready: 5 (warn/crit at 1/10)", [("messages_ready", 5, 1, 10)]),
                (
                    1,
                    "Messages unacknowledged: 5 (warn/crit at 1/10)",
                    [("messages_unacknowledged", 5, 1, 10)],
                ),
                (0, "Messages published: 5", [("messages_publish", 5, None, None)]),
                (
                    1,
                    # TODO: output is not rendered as float
                    "Rate: 0 1/s (warn/crit at 0 1/s/0 1/s)",
                    [("messages_publish_rate", 0.15, 0.1, 0.5)],
                ),
                (
                    1,
                    "Memory used: 16.4 KiB (warn/crit at 10.0 KiB/50.0 KiB)",
                    [("mem_lnx_total_used", 16780, 10240, 51200)],
                ),
            ],
            id="WARN for upper levels",
        ),
        pytest.param(
            [
                [
                    '{"memory": 16780, "message_stats": {"publish": 5, "publish_details": {"rate": 0.15}}, "messages": 5, "messages_ready": 5, "messages_unacknowledged": 5, "name": "my_queue", "node": "rabbit@my-rabbit", "state": "running", "type": "classic"}',
                ]
            ],
            {
                "msg_lower": (20, 10),
                "msg_ready_lower": (20, 10),
                "msg_unack_lower": (20, 10),
                "msg_publish_rate_lower": (0.5, 0.1),
            },
            [
                (0, "Type: Classic"),
                (0, "Is running: running"),
                (0, "Running on node: rabbit@my-rabbit"),
                (
                    2,
                    "Total number of messages: 5 (warn/crit below 20/10)",
                    [("messages", 5, None, None)],
                ),
                (
                    2,
                    "Messages ready: 5 (warn/crit below 20/10)",
                    [("messages_ready", 5, None, None)],
                ),
                (
                    2,
                    "Messages unacknowledged: 5 (warn/crit below 20/10)",
                    [("messages_unacknowledged", 5, None, None)],
                ),
                (0, "Messages published: 5", [("messages_publish", 5, None, None)]),
                (
                    1,
                    "Rate: 0 1/s (warn/crit below 0 1/s/0 1/s)",
                    [("messages_publish_rate", 0.15, None, None)],
                ),
                (0, "Memory used: 16.4 KiB", [("mem_lnx_total_used", 16780, None, None)]),
            ],
            id="CRIT for lower levels",
        ),
    ],
)
def test_check_rabbitmq_queues(
    string_table: StringTable, params: Mapping[str, Any], expected: CheckResult
) -> None:
    parsed = parse_rabbitmq_queues(string_table)
    assert expected == list(check_rabbitmq_queues("my_queue", params, parsed))
