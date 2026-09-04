#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.monitor.hosts._api._list_hosts import _handle_list_hosts
from cmk.gui.monitor.hosts._models import HostState

from .testlib import get_fake_host_repository, HostFactory


def test_handle_list_hosts_limit_handling() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, host_repo.count_total(), limit=7)

    assert len(response.hosts) == 7
    assert response.meta.limit == 7
    assert response.meta.total == 10
    assert response.meta.matched == 10


def test_handle_list_hosts_without_limit_returns_all() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, host_repo.count_total(), limit=None)

    assert len(response.hosts) == 10
    assert response.meta.limit is None
    assert response.meta.total == 10
    assert response.meta.matched == 10


def test_handle_list_hosts_state_label_conversion() -> None:
    host_repo = get_fake_host_repository(n_hosts=100)
    response = _handle_list_hosts(host_repo, host_repo.count_total())
    host_states = [host.state for host in response.hosts]

    assert all(state in {"UP", "DOWN", "UNREACHABLE", "PENDING"} for state in host_states)


def test_handle_list_hosts_pending_state_round_trips() -> None:
    hosts = [
        HostFactory.build(name="pending-host", state=HostState.PENDING),
        HostFactory.build(name="checked-host", state=HostState.UP),
    ]
    host_repo = get_fake_host_repository(hosts=hosts)
    response = _handle_list_hosts(host_repo, host_repo.count_total())

    state_by_name = {host.name: host.state for host in response.hosts}
    assert state_by_name == {"pending-host": "PENDING", "checked-host": "UP"}
