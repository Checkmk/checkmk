from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.rabbitmq.agent_based.queues import (
    check_rabbitmq_queues,
    DEFAULT_PARAMETERS,
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
            [Service(item="my_queue")],
            id="single_queue",
        ),
    ],
)
def test_discover_rabbitmq_queues(string_table: StringTable, expected: list[Service]) -> None:
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
            [Result(state=State.CRIT, summary="Is running: ")],
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
                Result(state=State.OK, summary="Type: Quorum"),
                Result(state=State.OK, summary="Is running: stopped"),
                Result(state=State.OK, summary="Running on node: rabbit@my-rabbit"),
                Result(state=State.OK, summary="Total number of messages: 0"),
                Metric("messages", 0.0),
                Result(state=State.OK, summary="Messages ready: 0"),
                Metric("messages_ready", 0.0),
                Result(state=State.OK, summary="Messages unacknowledged: 0"),
                Metric("messages_unacknowledged", 0.0),
                Result(state=State.OK, summary="Memory used: 66.4 KiB"),
                Metric("mem_lnx_total_used", 68036.0),
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
                Result(state=State.OK, summary="Type: Classic"),
                Result(state=State.OK, summary="Is running: stopped"),
                Result(state=State.OK, summary="Running on node: rabbit@my-rabbit"),
                Result(state=State.OK, summary="Total number of messages: 0"),
                Metric("messages", 0.0),
                Result(state=State.OK, summary="Messages ready: 0"),
                Metric("messages_ready", 0.0),
                Result(state=State.OK, summary="Messages unacknowledged: 0"),
                Metric("messages_unacknowledged", 0.0),
                Result(state=State.OK, summary="Memory used: 9.59 KiB"),
                Metric("mem_lnx_total_used", 9816.0),
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
                "msg_upper": ("fixed", (1, 10)),
                "msg_ready_upper": ("fixed", (1, 10)),
                "msg_unack_upper": ("fixed", (1, 10)),
                "msg_publish_upper": ("fixed", (1, 10)),
                "msg_publish_rate_upper": ("fixed", (0.1, 0.5)),
                "abs_memory": ("fixed", (10240, 51200)),
            },
            [
                Result(state=State.OK, summary="Type: Classic"),
                Result(state=State.OK, summary="Is running: running"),
                Result(state=State.OK, summary="Running on node: rabbit@my-rabbit"),
                Result(state=State.WARN, summary="Total number of messages: 5 (warn/crit at 1/10)"),
                Metric("messages", 5.0, levels=(1.0, 10.0)),
                Result(state=State.WARN, summary="Messages ready: 5 (warn/crit at 1/10)"),
                Metric("messages_ready", 5.0, levels=(1.0, 10.0)),
                Result(state=State.WARN, summary="Messages unacknowledged: 5 (warn/crit at 1/10)"),
                Metric("messages_unacknowledged", 5.0, levels=(1.0, 10.0)),
                Result(state=State.WARN, summary="Messages published: 5 (warn/crit at 1/10)"),
                Metric("messages_publish", 5.0, levels=(1.0, 10.0)),
                Result(state=State.WARN, summary="Rate: 0 1/s (warn/crit at 0 1/s/0 1/s)"),
                Metric("messages_publish_rate", 0.15, levels=(0.1, 0.5)),
                Result(
                    state=State.WARN,
                    summary="Memory used: 16.4 KiB (warn/crit at 10.0 KiB/50.0 KiB)",
                ),
                Metric("mem_lnx_total_used", 16780.0, levels=(10240.0, 51200.0)),
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
                "msg_lower": ("fixed", (20, 10)),
                "msg_ready_lower": ("fixed", (20, 10)),
                "msg_unack_lower": ("fixed", (20, 10)),
                "msg_publish_lower": ("fixed", (20, 10)),
                "msg_publish_rate_lower": ("fixed", (0.5, 0.1)),
            },
            [
                Result(state=State.OK, summary="Type: Classic"),
                Result(state=State.OK, summary="Is running: running"),
                Result(state=State.OK, summary="Running on node: rabbit@my-rabbit"),
                Result(
                    state=State.CRIT, summary="Total number of messages: 5 (warn/crit below 20/10)"
                ),
                Metric("messages", 5.0),
                Result(state=State.CRIT, summary="Messages ready: 5 (warn/crit below 20/10)"),
                Metric("messages_ready", 5.0),
                Result(
                    state=State.CRIT, summary="Messages unacknowledged: 5 (warn/crit below 20/10)"
                ),
                Metric("messages_unacknowledged", 5.0),
                Result(state=State.CRIT, summary="Messages published: 5 (warn/crit below 20/10)"),
                Metric("messages_publish", 5.0),
                Result(state=State.WARN, summary="Rate: 0 1/s (warn/crit below 0 1/s/0 1/s)"),
                Metric("messages_publish_rate", 0.15),
                Result(state=State.OK, summary="Memory used: 16.4 KiB"),
                Metric("mem_lnx_total_used", 16780.0),
            ],
        ),
    ],
)
def test_check_rabbitmq_queues(
    string_table: StringTable, params: Mapping[str, Any], expected: CheckResult
) -> None:
    parsed = parse_rabbitmq_queues(string_table)
    assert expected == list(
        check_rabbitmq_queues("my_queue", {**DEFAULT_PARAMETERS, **params}, parsed)
    )
