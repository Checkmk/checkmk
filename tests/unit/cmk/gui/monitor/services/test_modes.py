#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.monitor.services._api._modes import build_service_modes, build_service_modes_by_id

from .testlib import ServiceFactory, ServiceOverviewFactory

_HOSTNAME = "web-server-01"
_SITE_ID = "local"


def test_build_service_modes_by_id_none() -> None:
    service = ServiceFactory.build(
        in_downtime=False, acknowledged=False, notifications_enabled=True, is_flapping=False
    )
    assert build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID) == []


def test_build_service_modes_by_id_downtime() -> None:
    service = ServiceFactory.build(
        in_downtime=True, acknowledged=False, notifications_enabled=True, is_flapping=False
    )
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["downtime"]
    assert modes[0].link.startswith("view.py?")
    assert "downtimes_of_service" in modes[0].link


def test_build_service_modes_by_id_acknowledged() -> None:
    service = ServiceFactory.build(
        in_downtime=False, acknowledged=True, notifications_enabled=True, is_flapping=False
    )

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["ack"]


def test_build_service_modes_by_id_notifications_disabled() -> None:
    service = ServiceFactory.build(
        in_downtime=False, acknowledged=False, notifications_enabled=False, is_flapping=False
    )
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["notif-disabled"]
    assert modes[0].link.startswith("view.py?")


def test_build_service_modes_by_id_flapping_is_not_a_mode() -> None:
    # Flapping is shown in the state column instead, not as a mode icon.
    service = ServiceFactory.build(
        in_downtime=False, acknowledged=False, notifications_enabled=True, is_flapping=True
    )

    assert build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID) == []


def test_build_service_modes_by_id_downtime_and_acknowledged() -> None:
    service = ServiceFactory.build(
        in_downtime=True, acknowledged=True, notifications_enabled=True, is_flapping=False
    )

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["downtime", "ack"]


def test_build_service_modes_by_id_all_modes() -> None:
    service = ServiceFactory.build(
        in_downtime=True, acknowledged=True, notifications_enabled=False, is_flapping=True
    )

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["downtime", "ack", "notif-disabled"]


def test_build_service_modes_none() -> None:
    service = ServiceOverviewFactory.build(
        in_downtime=False, acknowledged=False, notifications_enabled=True, is_flapping=False
    )
    assert build_service_modes(service) == []


def test_build_service_modes_all_modes() -> None:
    service = ServiceOverviewFactory.build(
        in_downtime=True, acknowledged=True, notifications_enabled=False, is_flapping=True
    )

    assert [mode.icon_name for mode in build_service_modes(service)] == [
        "downtime",
        "ack",
        "notif-disabled",
    ]


def test_build_service_modes_flapping_is_not_a_mode() -> None:
    # Flapping is shown as its own badge next to the state in the slide-in header instead.
    service = ServiceOverviewFactory.build(
        in_downtime=False, acknowledged=False, notifications_enabled=True, is_flapping=True
    )

    assert build_service_modes(service) == []
