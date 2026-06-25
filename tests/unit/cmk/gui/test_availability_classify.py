#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.computation import classify_span_state
from cmk.gui.availability.options import get_default_avoptions
from cmk.gui.availability.type_defs import (
    AVObjectType,
    AVOptionConsider,
    AVOptionDowntimes,
    AVOptionHostStateGrouping,
    AVOptions,
    AVOptionStateGrouping,
    AVSpan,
)


def _span(
    *,
    state: int | None = 0,
    in_service_period: int = 1,
    in_notification_period: int = 1,
    in_downtime: int = 0,
    in_host_downtime: int = 0,
    host_down: int = 0,
    is_flapping: int = 0,
) -> AVSpan:
    return {
        "site": SiteId("heute"),
        "host_name": HostName("heute"),
        "service_description": "CPU load",
        "from": 0,
        "until": 60,
        "duration": 60,
        "state": state,
        "host_down": host_down,
        "in_downtime": in_downtime,
        "in_host_downtime": in_host_downtime,
        "in_notification_period": in_notification_period,
        "in_service_period": in_service_period,
        "is_flapping": is_flapping,
    }


def _avoptions(
    *,
    service_period: Literal["honor", "ignore", "exclude"] | None = None,
    notification_period: Literal["honor", "exclude", "ignore"] | None = None,
    consider: AVOptionConsider | None = None,
    downtimes: AVOptionDowntimes | None = None,
    host_state_grouping: AVOptionHostStateGrouping | None = None,
    state_grouping: AVOptionStateGrouping | None = None,
) -> AVOptions:
    avoptions = get_default_avoptions((0.0, 60.0))
    if service_period is not None:
        avoptions["service_period"] = service_period
    if notification_period is not None:
        avoptions["notification_period"] = notification_period
    if consider is not None:
        avoptions["consider"] = consider
    if downtimes is not None:
        avoptions["downtimes"] = downtimes
    if host_state_grouping is not None:
        avoptions["host_state_grouping"] = host_state_grouping
    if state_grouping is not None:
        avoptions["state_grouping"] = state_grouping
    return avoptions


@pytest.mark.parametrize(
    "what, span, avoptions, expected",
    [
        # --- plain service/host state classification ---
        pytest.param("service", _span(state=0), _avoptions(), ("ok", True), id="service-ok"),
        pytest.param("service", _span(state=1), _avoptions(), ("warn", True), id="service-warn"),
        pytest.param("service", _span(state=2), _avoptions(), ("crit", True), id="service-crit"),
        pytest.param(
            "service", _span(state=3), _avoptions(), ("unknown", True), id="service-unknown"
        ),
        pytest.param("host", _span(state=0), _avoptions(), ("up", True), id="host-up"),
        pytest.param("host", _span(state=1), _avoptions(), ("down", True), id="host-down"),
        pytest.param("host", _span(state=2), _avoptions(), ("unreach", True), id="host-unreach"),
        # --- service period ---
        pytest.param(
            "service",
            _span(in_service_period=0),
            _avoptions(),
            ("outof_service_period", False),
            id="service_period-honor-outside",
        ),
        pytest.param(
            "service",
            _span(in_service_period=0),
            _avoptions(service_period="ignore"),
            ("ok", True),
            id="service_period-ignore",
        ),
        pytest.param(
            "service",
            _span(in_service_period=1),
            _avoptions(service_period="exclude"),
            ("outof_service_period", False),
            id="service_period-exclude-inside",
        ),
        # --- unmonitored ---
        pytest.param(
            "service", _span(state=-1), _avoptions(), ("unmonitored", True), id="unmonitored"
        ),
        pytest.param(
            "service",
            _span(state=-1),
            _avoptions(consider={"flapping": True, "host_down": True, "unmonitored": False}),
            ("unmonitored", False),
            id="unmonitored-not-considered",
        ),
        # --- unknown-at-time (state None) is dropped ---
        pytest.param(
            "service", _span(state=None), _avoptions(), ("unmonitored", False), id="state-none"
        ),
        # --- notification period ---
        pytest.param(
            "service",
            _span(in_notification_period=0),
            _avoptions(notification_period="exclude"),
            ("unmonitored", False),
            id="notification_period-exclude",
        ),
        pytest.param(
            "service",
            _span(in_notification_period=0),
            _avoptions(notification_period="honor"),
            ("outof_notification_period", True),
            id="notification_period-honor",
        ),
        pytest.param(
            "service",
            _span(in_notification_period=0),
            _avoptions(notification_period="ignore"),
            ("ok", True),
            id="notification_period-ignore",
        ),
        # --- downtime ---
        pytest.param(
            "service",
            _span(in_downtime=1),
            _avoptions(),
            ("in_downtime", True),
            id="downtime-honor",
        ),
        pytest.param(
            "service",
            _span(in_host_downtime=1),
            _avoptions(),
            ("in_downtime", True),
            id="host-downtime-honor",
        ),
        pytest.param(
            "service",
            _span(in_downtime=1),
            _avoptions(downtimes={"include": "exclude", "exclude_ok": False}),
            ("unmonitored", False),
            id="downtime-exclude",
        ),
        pytest.param(
            "service",
            _span(in_downtime=1),
            _avoptions(downtimes={"include": "ignore", "exclude_ok": False}),
            ("ok", True),
            id="downtime-ignore",
        ),
        pytest.param(
            "service",
            _span(in_downtime=1, state=0),
            _avoptions(downtimes={"include": "honor", "exclude_ok": True}),
            ("ok", True),
            id="downtime-exclude_ok",
        ),
        pytest.param(
            "service",
            _span(in_downtime=1, state=2),
            _avoptions(downtimes={"include": "honor", "exclude_ok": True}),
            ("in_downtime", True),
            id="downtime-exclude_ok-non-ok-state",
        ),
        # --- host down (reclassification for services) ---
        pytest.param(
            "service",
            _span(host_down=1, state=1),
            _avoptions(),
            ("host_down", True),
            id="host_down-service",
        ),
        pytest.param(
            "service",
            _span(host_down=1, state=1),
            _avoptions(consider={"flapping": True, "host_down": False, "unmonitored": True}),
            ("warn", True),
            id="host_down-not-considered",
        ),
        pytest.param(
            "host",
            _span(host_down=1, state=1),
            _avoptions(),
            ("down", True),
            id="host_down-ignored-for-host",
        ),
        # --- flapping ---
        pytest.param(
            "service",
            _span(is_flapping=1, state=1),
            _avoptions(),
            ("flapping", True),
            id="flapping",
        ),
        pytest.param(
            "service",
            _span(is_flapping=1, state=1),
            _avoptions(consider={"flapping": False, "host_down": True, "unmonitored": True}),
            ("warn", True),
            id="flapping-not-considered",
        ),
        # --- state grouping ---
        pytest.param(
            "service",
            _span(state=1),
            _avoptions(
                state_grouping={"warn": "crit", "unknown": "unknown", "host_down": "host_down"}
            ),
            ("crit", True),
            id="state_grouping-warn-as-crit",
        ),
        pytest.param(
            "host",
            _span(state=2),
            _avoptions(host_state_grouping={"unreach": "down"}),
            ("down", True),
            id="host_state_grouping-unreach-as-down",
        ),
    ],
)
def test_classify_span_state(
    what: AVObjectType,
    span: AVSpan,
    avoptions: AVOptions,
    expected: tuple[str, bool],
) -> None:
    assert classify_span_state(span, avoptions, what) == expected
