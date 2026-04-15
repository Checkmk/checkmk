#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

# mypy: disable-error-code="misc"
# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple
from unittest import mock

from cmk.agent_based.v2 import Result, Service
from cmk.plugins.nginx.agent_based.nginx_status import (
    check_nginx_status,
    discover_nginx_status,
    parse_nginx_status,
)


class _MockValueStore:
    def __init__(self, getter: Callable[..., Any]) -> None:
        self._getter = getter

    def get(self, key: str, default: Any = None) -> Any:
        return self._getter(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        pass


class _MockVSManager(NamedTuple):
    active_service_interface: _MockValueStore


def mock_item_state(mock_state: Mapping[str, Any]) -> mock._patch[Any]:
    target = "cmk.agent_based.v1.value_store._active_host_value_store"
    getter = mock_state.get if isinstance(mock_state, dict) else mock_state
    return mock.patch(target, _MockVSManager(_MockValueStore(getter)))  # type: ignore[arg-type]


def test_nginx_status_regression_discovery() -> None:
    """Test discovery of nginx status endpoints."""
    string_table = [
        ["127.0.0.1", "80", "Active", "connections:", "10"],
        ["127.0.0.1", "80", "serveracceptshandledrequests"],
        ["127.0.0.1", "80", "12", "10", "120"],
        ["127.0.0.1", "80", "Reading:", "2", "Writing:", "1", "Waiting:", "3"],
        ["127.0.1.1", "80", "Active", "connections:", "24"],
        ["127.0.1.1", "80", "server", "accepts", "handled", "requests"],
        ["127.0.1.1", "80", "23", "42", "323"],
        ["127.0.1.1", "80", "Reading:", "1", "Writing:", "5", "Waiting:", "0"],
    ]

    parsed = parse_nginx_status(string_table)
    discovery = list(discover_nginx_status(parsed))
    assert len(discovery) == 2
    items = [s.item for s in discovery]
    assert "127.0.0.1:80" in items
    assert "127.0.1.1:80" in items
    for s in discovery:
        assert isinstance(s, Service)


def test_nginx_status_regression_check() -> None:
    """Test nginx status check basic functionality."""
    string_table = [
        ["127.0.0.1", "80", "Active", "connections:", "10"],
        ["127.0.0.1", "80", "serveracceptshandledrequests"],
        ["127.0.0.1", "80", "12", "10", "120"],
        ["127.0.0.1", "80", "Reading:", "2", "Writing:", "1", "Waiting:", "3"],
        ["127.0.1.1", "80", "Active", "connections:", "24"],
        ["127.0.1.1", "80", "server", "accepts", "handled", "requests"],
        ["127.0.1.1", "80", "23", "42", "323"],
        ["127.0.1.1", "80", "Reading:", "1", "Writing:", "5", "Waiting:", "0"],
    ]

    parsed = parse_nginx_status(string_table)

    mock_state = {
        "nginx_status.accepted": (1570000000.0, 12),
        "nginx_status.handled": (1570000000.0, 10),
        "nginx_status.requests": (1570000000.0, 120),
    }

    with mock_item_state(mock_state):
        results = list(check_nginx_status("127.0.0.1:80", {}, parsed))

    assert len(results) >= 3
    assert any(isinstance(r, Result) and "Active:" in r.summary for r in results)


def test_nginx_status_regression_check_second_server() -> None:
    """Test nginx status check for second server basic functionality."""
    string_table = [
        ["127.0.0.1", "80", "Active", "connections:", "10"],
        ["127.0.0.1", "80", "serveracceptshandledrequests"],
        ["127.0.0.1", "80", "12", "10", "120"],
        ["127.0.0.1", "80", "Reading:", "2", "Writing:", "1", "Waiting:", "3"],
        ["127.0.1.1", "80", "Active", "connections:", "24"],
        ["127.0.1.1", "80", "server", "accepts", "handled", "requests"],
        ["127.0.1.1", "80", "23", "42", "323"],
        ["127.0.1.1", "80", "Reading:", "1", "Writing:", "5", "Waiting:", "0"],
    ]

    parsed = parse_nginx_status(string_table)

    mock_state = {
        "nginx_status.accepted": (1570000000.0, 23),
        "nginx_status.handled": (1570000000.0, 42),
        "nginx_status.requests": (1570000000.0, 323),
    }

    with mock_item_state(mock_state):
        results = list(check_nginx_status("127.0.1.1:80", {}, parsed))

    assert len(results) >= 3
    assert any(isinstance(r, Result) and "Active:" in r.summary for r in results)
