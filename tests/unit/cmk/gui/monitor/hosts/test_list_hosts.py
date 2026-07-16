#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.monitor.hosts._api._list_hosts import (
    _handle_list_hosts,
    _MAX_NUMBER_OF_HOSTS,
    _resolve_limit,
)

from .testlib import get_fake_host_repository


def test_handle_list_hosts_limit_handling() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, limit=7)

    assert len(response.hosts) == 7
    assert response.meta.limit == 7
    assert response.meta.total == 10
    assert response.meta.matched == 10


def test_handle_list_hosts_without_limit_returns_all() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, limit=None)

    assert len(response.hosts) == 10
    assert response.meta.limit == 0
    assert response.meta.total == 10
    assert response.meta.matched == 10


@pytest.mark.parametrize(
    ["requested", "may_remove_limit", "expected"],
    [
        pytest.param(1000, False, 1000, id="numeric passes through without permission"),
        pytest.param(1000, True, 1000, id="numeric passes through with permission"),
        pytest.param(None, True, None, id="no limit honored with permission"),
        pytest.param(None, False, _MAX_NUMBER_OF_HOSTS, id="no limit clamped without permission"),
    ],
)
def test_resolve_limit(requested: int | None, may_remove_limit: bool, expected: int | None) -> None:
    assert _resolve_limit(requested, may_remove_limit=may_remove_limit) == expected


def test_handle_list_hosts_state_label_conversion() -> None:
    host_repo = get_fake_host_repository(n_hosts=100)
    response = _handle_list_hosts(host_repo)
    host_states = [host.state for host in response.hosts]

    assert all(state in {"UP", "DOWN", "UNREACHABLE"} for state in host_states)
