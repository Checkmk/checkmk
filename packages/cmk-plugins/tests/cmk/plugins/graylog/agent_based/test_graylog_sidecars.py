#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

from cmk.agent_based.v2 import Result, State
from cmk.plugins.graylog.agent_based.graylog_sidecars import (
    check_graylog_sidecars,
    discover_graylog_sidecars,
    parse_graylog_sidecars,
)


def test_discovery_graylog_sidecars() -> None:
    string_table = [
        [
            '{"node_name": "test-node-1", "active": true, "last_seen": "2024-01-01T12:00:00.000Z", "node_details": {"status": {"status": 0, "message": "1 running/0 stopped/0 failing"}}}'
        ],
        [
            '{"node_name": "test-node-2", "active": false, "last_seen": "2024-01-01T11:00:00.000Z", "node_details": {"status": {"status": 1, "message": "0 running/1 stopped/0 failing"}}}'
        ],
    ]
    parsed = parse_graylog_sidecars(string_table)
    assert sorted(s.item or "" for s in discover_graylog_sidecars(parsed)) == [
        "test-node-1",
        "test-node-2",
    ]


def test_check_graylog_sidecars_active_node() -> None:
    string_table = [
        ['{"node_name": "test-node-1", "active": true, "last_seen": "2024-01-01T12:00:00.000Z"}'],
    ]
    parsed = parse_graylog_sidecars(string_table)
    params: dict[str, Any] = {}

    results = list(check_graylog_sidecars("test-node-1", params, parsed))
    summaries = [r.summary for r in results if isinstance(r, Result)]
    assert any("Active: yes" in s for s in summaries)
    assert any("Last seen:" in s for s in summaries)


def test_check_graylog_sidecars_inactive_node() -> None:
    string_table = [
        ['{"node_name": "test-node-2", "active": false, "last_seen": "2024-01-01T11:00:00.000Z"}'],
    ]
    parsed = parse_graylog_sidecars(string_table)
    params: dict[str, Any] = {"active_state": 2}

    results = [
        r for r in check_graylog_sidecars("test-node-2", params, parsed) if isinstance(r, Result)
    ]
    active_result = next((r for r in results if "Active:" in r.summary), None)
    assert active_result is not None
    assert active_result.state is State.CRIT
    assert "Active: no" in active_result.summary


def test_check_graylog_sidecars_missing_item() -> None:
    string_table = [
        ['{"node_name": "test-node-1", "active": true, "last_seen": "2024-01-01T12:00:00.000Z"}'],
    ]
    parsed = parse_graylog_sidecars(string_table)
    assert list(check_graylog_sidecars("nonexistent-node", {}, parsed)) == []
