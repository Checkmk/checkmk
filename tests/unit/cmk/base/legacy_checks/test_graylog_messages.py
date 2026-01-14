#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Tests for graylog_messages legacy check."""

from typing import Any

import pytest

from cmk.base.check_legacy_includes import graylog
from cmk.base.legacy_checks import graylog_messages


@pytest.fixture
def empty_value_store(monkeypatch: pytest.MonkeyPatch) -> None:
    store = dict[str, object]()
    monkeypatch.setattr(graylog, "get_value_store", lambda: store)


def test_discovery_graylog_messages() -> None:
    """Test discovery function for graylog_messages."""
    # Sample graylog agent data with message statistics
    info = [
        ['{"events": 1000}'],
    ]

    parsed = graylog.parse_graylog_agent_data(info)
    result = list(graylog_messages.discover_graylog_messages(parsed))

    # Should discover one item with None as the item name
    assert len(result) == 1
    assert result[0][0] is None


def test_check_graylog_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test check function for graylog_messages."""
    # Sample graylog agent data with message statistics
    info = [
        ['{"events": 1000}'],
    ]

    parsed = graylog.parse_graylog_agent_data(info)
    params: dict[str, Any] = {}

    # Pre-populate value store to avoid GetRateError on first run
    monkeypatch.setattr(
        graylog, "get_value_store", lambda: {"graylog_msgs_avg.rate": (1670328674.09963, 900)}
    )

    result = list(graylog_messages.check_graylog_messages(None, params, parsed))

    # Should return 3 results: total messages, average rate, and message diff
    assert len(result) == 3

    # Check first result: Total number of messages
    state1, summary1, metrics1 = result[0]
    assert state1 == 0  # OK
    assert "Total number of messages: 1000" in summary1
    assert len(metrics1) == 1
    assert metrics1[0][0] == "messages"  # metric name
    assert metrics1[0][1] == 1000  # metric value

    # Check second result: Average number of messages
    state2, summary2, metrics2 = result[1]
    assert state2 == 0  # OK
    assert "Average number of messages" in summary2
    assert "30 minutes" in summary2
    assert len(metrics2) == 1
    assert metrics2[0][0] == "msgs_avg"  # metric name

    # Check third result: Messages since last check
    state3, summary3, metrics3 = result[2]
    assert state3 == 0  # OK
    assert "Total number of messages since last check" in summary3
    assert len(metrics3) == 1
    assert metrics3[0][0] == "graylog_diff"  # metric name
    assert metrics3[0][1] == 0  # should be 0 since it's the first run
