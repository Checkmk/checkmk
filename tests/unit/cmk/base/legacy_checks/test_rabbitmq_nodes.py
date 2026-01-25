#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


import time_machine

from cmk.base.legacy_checks.rabbitmq_nodes import (
    check_rabbitmq_nodes,
    check_rabbitmq_nodes_filedesc,
    check_rabbitmq_nodes_gc,
    check_rabbitmq_nodes_mem,
    check_rabbitmq_nodes_uptime,
    discover_key,
    discover_rabbitmq_nodes,
    parse_rabbitmq_nodes,
    Section,
)


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
    result = list(discover_rabbitmq_nodes(_section()))

    assert len(result) == 1
    assert result[0] == ("rabbit@my-rabbit", {})


def test_discover_key_filedesc() -> None:
    """Test discovery function for file descriptor service."""
    discover_func = discover_key("fd")
    result = list(discover_func(_section()))

    assert len(result) == 1
    assert result[0] == ("rabbit@my-rabbit", {})


def test_discover_key_mem() -> None:
    """Test discovery function for memory service."""
    discover_func = discover_key("mem")
    result = list(discover_func(_section()))
    assert len(result) == 1
    assert result[0] == ("rabbit@my-rabbit", {})


def test_discover_key_uptime() -> None:
    """Test discovery function for uptime service."""
    discover_func = discover_key("uptime")
    result = list(discover_func(_section()))

    assert len(result) == 1
    assert result[0] == ("rabbit@my-rabbit", {})


def test_discover_key_gc() -> None:
    """Test discovery function for garbage collection service."""
    discover_func = discover_key("gc")
    result = list(discover_func(_section()))
    assert len(result) == 1
    assert result[0] == ("rabbit@my-rabbit", {})


def test_check_rabbitmq_nodes_ok() -> None:
    """Test main RabbitMQ nodes check function with normal state."""
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    result = list(check_rabbitmq_nodes("rabbit@my-rabbit", params, _section()))

    assert result == [(0, "Type: Disc"), (0, "Is running: yes")]


def test_check_rabbitmq_nodes_with_alarms() -> None:
    """Test main RabbitMQ nodes check function with alarms triggered."""
    string_table = [
        [
            '{"name": "rabbit@test", "type": "disc", "running": true, "disk_free_alarm": true, "mem_alarm": true}'
        ]
    ]
    parsed = parse_rabbitmq_nodes(string_table)
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    result = list(check_rabbitmq_nodes("rabbit@test", params, parsed))

    assert len(result) == 4

    # Check that alarms trigger critical states
    state, summary = result[2][:2]
    assert state == 2  # Should be critical
    assert "Disk alarm in effect: yes" in summary

    state, summary = result[3][:2]
    assert state == 2  # Should be critical
    assert "Memory alarm in effect: yes" in summary


def test_check_rabbitmq_nodes_not_running() -> None:
    """Test main RabbitMQ nodes check function when node is not running."""
    string_table = [
        [
            '{"name": "rabbit@test", "type": "disc", "running": false, "disk_free_alarm": false, "mem_alarm": false}'
        ]
    ]
    parsed = parse_rabbitmq_nodes(string_table)
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    result = list(check_rabbitmq_nodes("rabbit@test", params, parsed))

    assert len(result) == 2

    # Check running state
    state, summary = result[1][:2]
    assert state == 2  # Should be critical when not running
    assert "Is running: no" in summary


def test_check_rabbitmq_nodes_missing_item() -> None:
    """Test main RabbitMQ nodes check function with missing item."""
    params = {"state": 2, "disk_free_alarm": 2, "mem_alarm": 2}

    result = list(check_rabbitmq_nodes("missing@item", params, _section()))
    assert len(result) == 0


def test_check_rabbitmq_nodes_filedesc() -> None:
    """Test RabbitMQ file descriptor check function."""
    result = list(check_rabbitmq_nodes_filedesc("rabbit@my-rabbit", {}, _section()))

    assert len(result) == 2

    # Check file descriptors usage
    state, summary, metrics = result[0]
    assert state == 0
    assert "File descriptors used: 34 of 1048576, <0.01%" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "open_file_descriptors"
    assert metrics[0][1] == 34
    assert metrics[0][4] == 0  # min
    assert metrics[0][5] == 1048576  # max

    # Check file descriptor open attempts
    state, summary, metrics = result[1]
    assert state == 0
    assert "File descriptor open attempts: 11" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "file_descriptors_open_attempts"
    assert metrics[0][1] == 11


def test_check_rabbitmq_nodes_filedesc_with_thresholds() -> None:
    """Test RabbitMQ file descriptor check function with thresholds."""
    string_table = [
        [
            '{"name": "rabbit@test", "fd_used": 800000, "fd_total": 1000000, "io_file_handle_open_attempt_count": 500}'
        ]
    ]
    parsed = parse_rabbitmq_nodes(string_table)
    # The levels parameter should be a tuple of warn/crit values
    params = {"levels": ((None, None), (70.0, 90.0)), "fd_open_upper": (400, 600)}

    result = list(check_rabbitmq_nodes_filedesc("rabbit@test", params, parsed))

    assert len(result) == 2

    # Should trigger warning for high file descriptor usage (80% > 70%)
    state, summary, metrics = result[0]
    assert state == 1  # Warning
    assert "File descriptors used: 800000 of 1000000, 80.00%" in summary
    assert "(warn/crit at 70.00%/90.00%)" in summary

    # Should trigger warning for high open attempts (500 > 400)
    state, summary, metrics = result[1]
    assert state == 1  # Warning


def test_check_rabbitmq_nodes_filedesc_missing_item() -> None:
    """Test RabbitMQ file descriptor check function with missing item."""
    result = list(check_rabbitmq_nodes_filedesc("missing@item", {}, _section()))

    assert len(result) == 0


def test_check_rabbitmq_nodes_mem() -> None:
    """Test RabbitMQ memory check function."""
    params = {"levels": None}

    result = list(check_rabbitmq_nodes_mem("rabbit@my-rabbit", params, _section()))
    assert len(result) == 1

    state, summary, metrics = result[0]
    assert state == 0
    assert "Memory used: 1.71% - 108 MiB of 6.15 GiB High watermark" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "mem_used"
    assert metrics[0][1] == 113299456
    assert metrics[0][4] == 0  # min
    assert metrics[0][5] == 6608874700  # max


def test_check_rabbitmq_nodes_mem_with_percentage_thresholds() -> None:
    """Test RabbitMQ memory check function with percentage thresholds."""
    string_table = [['{"name": "rabbit@test", "mem_used": 5000000000, "mem_limit": 6000000000}']]
    parsed = parse_rabbitmq_nodes(string_table)
    params = {"levels": (80.0, 90.0)}

    result = list(check_rabbitmq_nodes_mem("rabbit@test", params, parsed))

    assert len(result) == 1

    # Should trigger warning for high memory usage (83.3% > 80%)
    state, summary, metrics = result[0]
    assert state == 1  # Warning


def test_check_rabbitmq_nodes_mem_with_absolute_thresholds() -> None:
    """Test RabbitMQ memory check function with absolute thresholds."""
    string_table = [['{"name": "rabbit@test", "mem_used": 5000000000, "mem_limit": 6000000000}']]
    parsed = parse_rabbitmq_nodes(string_table)
    params = {"levels": (4500000000, 5500000000)}  # Absolute values

    (result,) = list(check_rabbitmq_nodes_mem("rabbit@test", params, parsed))

    # Should trigger warning for high memory usage (5GB > 4.5GB)
    assert result[0] == 1


def test_check_rabbitmq_nodes_mem_missing_item() -> None:
    """Test RabbitMQ memory check function with missing item."""
    params = {"levels": None}

    assert not list(check_rabbitmq_nodes_mem("missing@item", params, _section()))


@time_machine.travel("2020-03-18 15:38:00")
def test_check_rabbitmq_nodes_uptime() -> None:
    """Test RabbitMQ uptime check function."""
    assert list(check_rabbitmq_nodes_uptime("rabbit@my-rabbit", {}, _section())) == [
        (0, "Up since Wed Mar 18 08:50:10 2020", []),
        (0, "Uptime: 6:47:49", [("uptime", 24469.577, None, None)]),
    ]


def test_check_rabbitmq_nodes_uptime_missing_item() -> None:
    """Test RabbitMQ uptime check function with missing item."""
    result = list(check_rabbitmq_nodes_uptime("missing@item", {}, _section()))

    assert len(result) == 0


def test_check_rabbitmq_nodes_gc() -> None:
    """Test RabbitMQ garbage collection check function."""
    result = list(check_rabbitmq_nodes_gc("rabbit@my-rabbit", {}, _section()))

    assert len(result) == 3

    # Check GC runs
    state, summary, metrics = result[0]
    assert state == 0
    assert "GC runs: 282855" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "gc_runs"
    assert metrics[0][1] == 282855

    # Check bytes reclaimed by GC
    state, summary, metrics = result[1]
    assert state == 0
    assert "Bytes reclaimed by GC: 16.0 GiB" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "gc_bytes"
    assert metrics[0][1] == 17144463144

    # Check runtime run queue
    state, summary, metrics = result[2]
    assert state == 0
    assert "Runtime run queue: 1" in summary
    assert len(metrics) == 1
    assert metrics[0][0] == "runtime_run_queue"
    assert metrics[0][1] == 1


def test_check_rabbitmq_nodes_gc_with_thresholds() -> None:
    """Test RabbitMQ garbage collection check function with thresholds."""
    string_table = [
        [
            '{"name": "rabbit@test", "gc_num": 500000, "gc_bytes_reclaimed": 20000000000, "run_queue": 10}'
        ]
    ]
    parsed = parse_rabbitmq_nodes(string_table)
    params = {
        "gc_num_upper": ("levels", (400000, 600000)),
        "gc_bytes_reclaimed_upper": ("levels", (15000000000, 25000000000)),
        "run_queue_upper": ("levels", (8, 12)),
    }

    result = list(check_rabbitmq_nodes_gc("rabbit@test", params, parsed))

    assert len(result) == 3

    # GC runs should trigger warning
    state, summary, metrics = result[0]
    assert state == 1  # Warning

    # Bytes reclaimed should trigger warning
    state, summary, metrics = result[1]
    assert state == 1  # Warning

    # Run queue should trigger warning
    state, summary, metrics = result[2]
    assert state == 1  # Warning


def test_check_rabbitmq_nodes_gc_missing_item() -> None:
    """Test RabbitMQ garbage collection check function with missing item."""
    result = list(check_rabbitmq_nodes_gc("missing@item", {}, _section()))

    assert len(result) == 0


def test_check_rabbitmq_nodes_partial_data() -> None:
    """Test RabbitMQ checks with partial data availability."""
    string_table = [
        [
            '{"name": "rabbit@test", "type": "disc", "running": true}'  # Only basic data
        ]
    ]
    parsed = parse_rabbitmq_nodes(string_table)

    # Main check should work with minimal data
    result = list(check_rabbitmq_nodes("rabbit@test", {"state": 2}, parsed))
    assert len(result) == 2

    # Sub-checks should return empty when data is missing
    assert len(list(check_rabbitmq_nodes_filedesc("rabbit@test", {}, parsed))) == 0
    assert len(list(check_rabbitmq_nodes_mem("rabbit@test", {}, parsed))) == 0
    assert len(list(check_rabbitmq_nodes_uptime("rabbit@test", {}, parsed))) == 0
    assert len(list(check_rabbitmq_nodes_gc("rabbit@test", {}, parsed))) == 0


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
    result = parse_rabbitmq_nodes(string_table)
    assert result == {}
