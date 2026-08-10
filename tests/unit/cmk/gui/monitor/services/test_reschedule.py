#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Sequence

from cmk.gui.monitor.services._api._reschedule import (
    _handle_reschedule_checks,
    RescheduleServiceRef,
)
from cmk.gui.monitor.services._models import RescheduleTarget

# datetime has microsecond resolution, so the round-trip through
# datetime.fromtimestamp can shave a sub-microsecond fraction off the captured
# time. Allow that when asserting a check time is not scheduled in the past.
_DATETIME_RESOLUTION_S = 1e-6


class _FakeServiceRescheduler:
    def __init__(self) -> None:
        self.targets: list[RescheduleTarget] = []

    def reschedule(self, targets: Sequence[RescheduleTarget]) -> None:
        self.targets = list(targets)


def _service(site_id: str, host_name: str, name: str) -> RescheduleServiceRef:
    return RescheduleServiceRef(site_id=site_id, host_name=host_name, name=name)


def test_handle_reschedule_checks_empty_services_does_not_touch_rescheduler() -> None:
    rescheduler = _FakeServiceRescheduler()

    response = _handle_reschedule_checks(rescheduler, services=[], spread_minutes=5)

    assert response.rescheduled == 0
    assert rescheduler.targets == []


def test_handle_reschedule_checks_reschedules_every_service() -> None:
    rescheduler = _FakeServiceRescheduler()
    services = [
        _service("local", "web-01", "CPU load"),
        _service("remote", "web-02", "Memory"),
    ]

    response = _handle_reschedule_checks(rescheduler, services=services, spread_minutes=0)

    assert response.rescheduled == 2
    assert [(t.site_id, t.host_name, t.description) for t in rescheduler.targets] == [
        ("local", "web-01", "CPU load"),
        ("remote", "web-02", "Memory"),
    ]


def test_handle_reschedule_checks_without_spread_schedules_immediately() -> None:
    rescheduler = _FakeServiceRescheduler()
    services = [
        _service("local", "web-01", "CPU load"),
        _service("local", "web-01", "Memory"),
    ]

    before = time.time()
    _handle_reschedule_checks(rescheduler, services=services, spread_minutes=0)
    after = time.time()

    for target in rescheduler.targets:
        assert before - _DATETIME_RESOLUTION_S <= target.check_time.timestamp() <= after


def test_handle_reschedule_checks_spreads_over_the_requested_window() -> None:
    rescheduler = _FakeServiceRescheduler()
    services = [_service("local", "web-01", f"Filesystem /mnt/{index}") for index in range(4)]

    before = time.time()
    _handle_reschedule_checks(rescheduler, services=services, spread_minutes=10)
    after = time.time()

    check_times = [target.check_time.timestamp() for target in rescheduler.targets]

    assert before - _DATETIME_RESOLUTION_S <= check_times[0] <= after
    assert check_times == sorted(check_times)
    assert check_times[-1] <= after + 10 * 60
