#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from polyfactory.factories import DataclassFactory

from cmk.gui.monitor.hosts._api._list_hosts import _handle_list_hosts
from cmk.gui.monitor.hosts._models import Host
from cmk.gui.monitor.hosts._repositories import HostRepository


class HostFactory(DataclassFactory[Host]):
    __check_model__ = False


def get_fake_host_repository(*, n_hosts: int) -> HostRepository:
    class HostFakeRepository:
        def __init__(self) -> None:
            self._hosts = [HostFactory.build() for _ in range(n_hosts)]

        def fetch(self, *, limit: int) -> Sequence[Host]:
            return self._hosts[:limit]

        def count(self) -> int:
            return len(self._hosts)

    return HostFakeRepository()


def test_handle_list_hosts_limit_handling() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, limit=7)

    assert len(response.hosts) == 7
    assert response.meta.limit == 7
    assert response.meta.total == 10


def test_handle_list_hosts_state_label_conversion() -> None:
    host_repo = get_fake_host_repository(n_hosts=100)
    response = _handle_list_hosts(host_repo, limit=100)
    host_states = [host.state for host in response.hosts]

    assert all(state in {"UP", "DOWN", "UNREACHABLE"} for state in host_states)
