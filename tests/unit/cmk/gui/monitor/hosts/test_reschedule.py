#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Sequence

from cmk.gui.monitor.hosts._api._reschedule import _handle_reschedule_checks, RescheduleHostRef
from cmk.gui.monitor.hosts._models import RescheduleTarget

# datetime has microsecond resolution, so the round-trip through
# datetime.fromtimestamp can shave a sub-microsecond fraction off the captured
# time. Allow that when asserting a check time is not scheduled in the past.
_DATETIME_RESOLUTION_S = 1e-6


class _FakeHostRescheduler:
    def __init__(self) -> None:
        self.targets: list[RescheduleTarget] = []

    def reschedule(self, targets: Sequence[RescheduleTarget]) -> None:
        self.targets = list(targets)


def _host(site_id: str, name: str) -> RescheduleHostRef:
    return RescheduleHostRef(site_id=site_id, name=name)


def test_handle_reschedule_checks_empty_hosts_does_not_touch_rescheduler() -> None:
    rescheduler = _FakeHostRescheduler()

    response = _handle_reschedule_checks(rescheduler, hosts=[], spread_minutes=5)

    assert response.rescheduled == 0
    assert rescheduler.targets == []


def test_handle_reschedule_checks_reschedules_every_host() -> None:
    rescheduler = _FakeHostRescheduler()
    hosts = [_host("local", "web-01"), _host("remote", "web-02")]

    response = _handle_reschedule_checks(rescheduler, hosts=hosts, spread_minutes=0)

    assert response.rescheduled == 2
    assert [(t.site_id, t.host_name) for t in rescheduler.targets] == [
        ("local", "web-01"),
        ("remote", "web-02"),
    ]


def test_handle_reschedule_checks_without_spread_schedules_immediately() -> None:
    rescheduler = _FakeHostRescheduler()
    hosts = [_host("local", "web-01"), _host("local", "web-02")]

    before = time.time()
    _handle_reschedule_checks(rescheduler, hosts=hosts, spread_minutes=0)
    after = time.time()

    for target in rescheduler.targets:
        assert before - _DATETIME_RESOLUTION_S <= target.check_time.timestamp() <= after


def test_handle_reschedule_checks_spreads_over_the_requested_window() -> None:
    rescheduler = _FakeHostRescheduler()
    hosts = [_host("local", f"web-{index:02}") for index in range(4)]

    before = time.time()
    _handle_reschedule_checks(rescheduler, hosts=hosts, spread_minutes=10)
    after = time.time()

    check_times = [target.check_time.timestamp() for target in rescheduler.targets]

    assert before - _DATETIME_RESOLUTION_S <= check_times[0] <= after
    assert check_times == sorted(check_times)
    assert check_times[-1] <= after + 10 * 60
