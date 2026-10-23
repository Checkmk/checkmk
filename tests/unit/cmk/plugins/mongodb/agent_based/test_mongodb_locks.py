#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.mongodb.agent_based.mongodb_locks import (
    check_mongodb_locks,
    discover_mongodb_locks,
    parse_mongodb_locks,
)

SECTION = parse_mongodb_locks(
    [
        ["activeClients", "readers", "0"],
        ["activeClients", "total", "53"],
        ["currentQueue", "writers", "5"],
    ]
)


def test_single_service_is_discovered_for_non_empty_section() -> None:
    assert list(discover_mongodb_locks(SECTION)) == [Service()]


def test_nothing_is_discovered_for_empty_section() -> None:
    assert not list(discover_mongodb_locks([]))


def test_clients_and_queue_are_checked_against_their_levels() -> None:
    assert list(check_mongodb_locks({"queue_writers_locks": (2, 10)}, SECTION)) == [
        Result(state=State.OK, summary="Clients-Readers: 0.00"),
        Metric("clients_readers_locks", 0),
        Result(state=State.OK, summary="Clients-Total: 53.00"),
        Metric("clients_total_locks", 53),
        Result(state=State.WARN, summary="Queue-Writers: 5.00 (warn/crit at 2.00/10.00)"),
        Metric("queue_writers_locks", 5, levels=(2, 10)),
    ]
