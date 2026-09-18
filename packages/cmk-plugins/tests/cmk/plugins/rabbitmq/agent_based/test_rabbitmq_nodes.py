#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.rabbitmq.agent_based.nodes import (
    check_rabbitmq_nodes,
    check_rabbitmq_nodes_filedesc,
    check_rabbitmq_nodes_gc,
    check_rabbitmq_nodes_mem,
    check_rabbitmq_nodes_uptime,
    discover_rabbitmq_nodes,
    parse_rabbitmq_nodes,
)
from cmk.plugins.rabbitmq.lib import discover_key, Section


def _section() -> Section:
    return parse_rabbitmq_nodes(
        [
            [
                '{"fd_total": 1048576, "sockets_total": 943629, "mem_limit": 6608874700, "mem_alarm": false, "disk_free_limit": 50000000, "disk_free_alarm": false, "proc_total": 1048576, "uptime": 24469577, "run_queue": 1, "name": "rabbit@my-rabbit", "type": "disc", "running": true, "mem_used": 113299456, "fd_used": 34, "sockets_used": 0, "proc_used": 431, "gc_num": 282855, "gc_bytes_reclaimed": 17144463144, "io_file_handle_open_attempt_count": 11}'
            ]
        ]
    )


def test_discover_rabbitmq_nodes() -> None:
    """Test discovery of main RabbitMQ nodes service."""
    assert list(discover_rabbitmq_nodes(_section())) == [Service(item="rabbit@my-rabbit")]


def test_discover_key_filedesc() -> None:
    """Test discovery function for file descriptor service."""
    assert list(discover_key("fd")(_section())) == [Service(item="rabbit@my-rabbit")]


def test_discover_key_mem() -> None:
    """Test discovery function for memory service."""
    assert list(discover_key("mem")(_section())) == [Service(item="rabbit@my-rabbit")]


def test_discover_key_uptime() -> None:
    """Test discovery function for uptime service."""
    assert list(discover_key("uptime")(_section())) == [Service(item="rabbit@my-rabbit")]


def test_discover_key_gc() -> None:
    """Test discovery function for garbage collection service."""
    assert list(discover_key("gc")(_section())) == [Service(item="rabbit@my-rabbit")]


def test_check_rabbitmq_nodes_ok() -> None:
    """Test main RabbitMQ nodes check function with normal state."""
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    assert list(check_rabbitmq_nodes("rabbit@my-rabbit", params, _section())) == [
        Result(state=State.OK, summary="Type: Disc"),
        Result(state=State.OK, summary="Is running: yes"),
    ]


def test_check_rabbitmq_nodes_with_alarms() -> None:
    """Test main RabbitMQ nodes check function with alarms triggered."""
    parsed = parse_rabbitmq_nodes(
        [
            [
                '{"name": "rabbit@test", "type": "disc", "running": true, "disk_free_alarm": true, "mem_alarm": true}'
            ]
        ]
    )
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    assert list(check_rabbitmq_nodes("rabbit@test", params, parsed)) == [
        Result(state=State.OK, summary="Type: Disc"),
        Result(state=State.OK, summary="Is running: yes"),
        Result(state=State.CRIT, summary="Disk alarm in effect: yes"),
        Result(state=State.CRIT, summary="Memory alarm in effect: yes"),
    ]


def test_check_rabbitmq_nodes_not_running() -> None:
    """Test main RabbitMQ nodes check function when node is not running."""
    parsed = parse_rabbitmq_nodes(
        [
            [
                '{"name": "rabbit@test", "type": "disc", "running": false, "disk_free_alarm": false, "mem_alarm": false}'
            ]
        ]
    )
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    assert list(check_rabbitmq_nodes("rabbit@test", params, parsed)) == [
        Result(state=State.OK, summary="Type: Disc"),
        Result(state=State.CRIT, summary="Is running: no"),
    ]


def test_check_rabbitmq_nodes_missing_item() -> None:
    """Test main RabbitMQ nodes check function with missing item."""
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    assert not list(check_rabbitmq_nodes("missing@item", params, _section()))


def test_check_rabbitmq_nodes_filedesc() -> None:
    """Test RabbitMQ file descriptor check function."""
    assert list(check_rabbitmq_nodes_filedesc("rabbit@my-rabbit", {}, _section())) == [
        Result(state=State.OK, summary="File descriptors used: 34 of 1048576, <0.01%"),
        Metric("open_file_descriptors", 34.0, boundaries=(0.0, 1048576.0)),
        Result(state=State.OK, summary="File descriptor open attempts: 11"),
        Metric("file_descriptors_open_attempts", 11.0),
    ]


def test_check_rabbitmq_nodes_filedesc_with_thresholds() -> None:
    """Test RabbitMQ file descriptor check function with thresholds."""
    parsed = parse_rabbitmq_nodes(
        [
            [
                '{"name": "rabbit@test", "fd_used": 800000, "fd_total": 1000000, "io_file_handle_open_attempt_count": 500}'
            ]
        ]
    )
    # The levels parameter should be a tuple of warn/crit values
    params = {"levels": ((None, None), (70.0, 90.0)), "fd_open_upper": (400, 600)}

    assert list(check_rabbitmq_nodes_filedesc("rabbit@test", params, parsed)) == [
        Result(
            state=State.WARN,
            summary=(
                "File descriptors used: 800000 of 1000000, 80.00% (warn/crit at 70.00%/90.00%)"
            ),
        ),
        Metric(
            "open_file_descriptors",
            800000.0,
            levels=(700000.0, 900000.0),
            boundaries=(0.0, 1000000.0),
        ),
        Result(
            state=State.WARN, summary="File descriptor open attempts: 500 (warn/crit at 400/600)"
        ),
        Metric("file_descriptors_open_attempts", 500.0, levels=(400.0, 600.0)),
    ]


def test_check_rabbitmq_nodes_filedesc_missing_item() -> None:
    """Test RabbitMQ file descriptor check function with missing item."""
    assert not list(check_rabbitmq_nodes_filedesc("missing@item", {}, _section()))


def test_check_rabbitmq_nodes_mem() -> None:
    """Test RabbitMQ memory check function."""
    assert list(check_rabbitmq_nodes_mem("rabbit@my-rabbit", {"levels": None}, _section())) == [
        Result(state=State.OK, summary="Memory used: 1.71% - 108 MiB of 6.15 GiB High watermark"),
        Metric("mem_used", 113299456.0, boundaries=(0.0, 6608874700.0)),
    ]


def test_check_rabbitmq_nodes_mem_with_percentage_thresholds() -> None:
    """Test RabbitMQ memory check function with percentage thresholds."""
    parsed = parse_rabbitmq_nodes(
        [['{"name": "rabbit@test", "mem_used": 5000000000, "mem_limit": 6000000000}']]
    )

    assert list(check_rabbitmq_nodes_mem("rabbit@test", {"levels": (80.0, 90.0)}, parsed)) == [
        Result(
            state=State.WARN,
            summary=(
                "Memory used: 83.33% - 4.66 GiB of 5.59 GiB High watermark"
                " (warn/crit at 80.00%/90.00% used)"
            ),
        ),
        Metric(
            "mem_used",
            5000000000.0,
            levels=(4800000000.0, 5400000000.0),
            boundaries=(0.0, 6000000000.0),
        ),
    ]


def test_check_rabbitmq_nodes_mem_with_absolute_thresholds() -> None:
    """Test RabbitMQ memory check function with absolute thresholds."""
    parsed = parse_rabbitmq_nodes(
        [['{"name": "rabbit@test", "mem_used": 5000000000, "mem_limit": 6000000000}']]
    )
    params = {"levels": (4500000000, 5500000000)}  # Absolute values

    assert list(check_rabbitmq_nodes_mem("rabbit@test", params, parsed)) == [
        Result(
            state=State.WARN,
            summary=(
                "Memory used: 83.33% - 4.66 GiB of 5.59 GiB High watermark"
                " (warn/crit at 4.19 GiB/5.12 GiB used)"
            ),
        ),
        Metric(
            "mem_used",
            5000000000.0,
            levels=(4500000000.0, 5500000000.0),
            boundaries=(0.0, 6000000000.0),
        ),
    ]


def test_check_rabbitmq_nodes_mem_missing_item() -> None:
    """Test RabbitMQ memory check function with missing item."""
    assert not list(check_rabbitmq_nodes_mem("missing@item", {"levels": None}, _section()))


@time_machine.travel("2020-03-18 15:38:00")
def test_check_rabbitmq_nodes_uptime() -> None:
    """Test RabbitMQ uptime check function."""
    assert list(check_rabbitmq_nodes_uptime("rabbit@my-rabbit", {}, _section())) == [
        Result(state=State.OK, summary="Up since Wed Mar 18 08:50:10 2020"),
        Result(state=State.OK, summary="Uptime: 6:47:49"),
        Metric("uptime", 24469.577),
    ]


def test_check_rabbitmq_nodes_uptime_missing_item() -> None:
    """Test RabbitMQ uptime check function with missing item."""
    assert not list(check_rabbitmq_nodes_uptime("missing@item", {}, _section()))


def test_check_rabbitmq_nodes_gc() -> None:
    """Test RabbitMQ garbage collection check function."""
    assert list(check_rabbitmq_nodes_gc("rabbit@my-rabbit", {}, _section())) == [
        Result(state=State.OK, summary="GC runs: 282855"),
        Metric("gc_runs", 282855.0),
        Result(state=State.OK, summary="Bytes reclaimed by GC: 16.0 GiB"),
        Metric("gc_bytes", 17144463144.0),
        Result(state=State.OK, summary="Runtime run queue: 1"),
        Metric("runtime_run_queue", 1.0),
    ]


def test_check_rabbitmq_nodes_gc_with_thresholds() -> None:
    """Test RabbitMQ garbage collection check function with thresholds."""
    parsed = parse_rabbitmq_nodes(
        [
            [
                '{"name": "rabbit@test", "gc_num": 500000, "gc_bytes_reclaimed": 20000000000, "run_queue": 10}'
            ]
        ]
    )
    params = {
        "gc_num_upper": ("fixed", (400000, 600000)),
        "gc_bytes_reclaimed_upper": ("fixed", (15000000000, 25000000000)),
        "run_queue_upper": ("fixed", (8, 12)),
    }

    assert list(check_rabbitmq_nodes_gc("rabbit@test", params, parsed)) == [
        Result(state=State.WARN, summary="GC runs: 500000 (warn/crit at 400000/600000)"),
        Metric("gc_runs", 500000.0, levels=(400000.0, 600000.0)),
        Result(
            state=State.WARN,
            summary="Bytes reclaimed by GC: 18.6 GiB (warn/crit at 14.0 GiB/23.3 GiB)",
        ),
        Metric("gc_bytes", 20000000000.0, levels=(15000000000.0, 25000000000.0)),
        Result(state=State.WARN, summary="Runtime run queue: 10 (warn/crit at 8/12)"),
        Metric("runtime_run_queue", 10.0, levels=(8.0, 12.0)),
    ]


def test_check_rabbitmq_nodes_gc_missing_item() -> None:
    """Test RabbitMQ garbage collection check function with missing item."""
    assert not list(check_rabbitmq_nodes_gc("missing@item", {}, _section()))


def test_check_rabbitmq_nodes_partial_data() -> None:
    """Test RabbitMQ checks with partial data availability."""
    parsed = parse_rabbitmq_nodes(
        [['{"name": "rabbit@test", "type": "disc", "running": true}']]  # Only basic data
    )

    # Main check should work with minimal data
    assert list(check_rabbitmq_nodes("rabbit@test", {"state": 2}, parsed)) == [
        Result(state=State.OK, summary="Type: Disc"),
        Result(state=State.OK, summary="Is running: yes"),
    ]

    # Sub-checks should return empty when data is missing
    assert not list(check_rabbitmq_nodes_filedesc("rabbit@test", {}, parsed))
    assert not list(check_rabbitmq_nodes_mem("rabbit@test", {}, parsed))
    assert not list(check_rabbitmq_nodes_uptime("rabbit@test", {}, parsed))
    assert not list(check_rabbitmq_nodes_gc("rabbit@test", {}, parsed))


def test_parse_rabbitmq_nodes_multiple_nodes() -> None:
    """Test parsing multiple RabbitMQ nodes."""
    string_table = [
        [
            '{"name": "rabbit1@test", "type": "disc", "running": true, "mem_used": 1000000, "mem_limit": 2000000}',
            '{"name": "rabbit2@test", "type": "ram", "running": false, "mem_used": 1500000, "mem_limit": 2000000}',
        ]
    ]

    result = parse_rabbitmq_nodes(string_table)

    assert len(result) == 2
    assert "rabbit1@test" in result
    assert "rabbit2@test" in result

    assert result["rabbit1@test"]["type"] == "disc"
    assert result["rabbit1@test"]["state"] is True
    assert result["rabbit2@test"]["type"] == "ram"
    assert result["rabbit2@test"]["state"] is False


def test_parse_rabbitmq_nodes_missing_name() -> None:
    """Test parsing with JSON missing node name."""
    string_table = [
        [
            '{"type": "disc", "running": true}'  # Missing "name" field
        ]
    ]

    # Should handle missing name gracefully and return empty dict
    assert parse_rabbitmq_nodes(string_table) == {}
