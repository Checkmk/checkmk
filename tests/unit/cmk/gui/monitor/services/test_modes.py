#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.monitor.services._api._modes import build_service_modes, build_service_modes_by_id

from .testlib import ServiceFactory, ServiceOverviewFactory

_HOSTNAME = "web-server-01"
_SITE_ID = "local"

# The factory randomises every field, so a test that asserts on one mode has to pin all the
# others to the value that keeps their icon away. Flapping is in here because it is deliberately
# not a mode - it has its own state-column badge.
_NO_MODES = {
    "in_downtime": False,
    "acknowledged": False,
    "notifications_enabled": True,
    "num_comments": 0,
    "active_checks_disabled": False,
    "passive_checks_disabled": False,
    "in_notification_period": True,
    "is_flapping": False,
}


def test_build_service_modes_by_id_none() -> None:
    service = ServiceFactory.build(**_NO_MODES)
    assert build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID) == []


def test_build_service_modes_by_id_downtime() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"in_downtime": True})
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["downtime"]
    assert modes[0].link.startswith("view.py?")
    assert "downtimes_of_service" in modes[0].link


def test_build_service_modes_by_id_acknowledged() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"acknowledged": True})

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["ack"]


def test_build_service_modes_by_id_notifications_disabled() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"notifications_enabled": False})
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["notif-disabled"]
    assert modes[0].link.startswith("view.py?")


def test_build_service_modes_by_id_comments() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"num_comments": 1})
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["comment"]
    assert "comments_of_service" in modes[0].link
    assert modes[0].title == "This service has 1 comment"


def test_build_service_modes_by_id_active_checks_disabled() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"active_checks_disabled": True})

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["disabled"]


def test_build_service_modes_by_id_passive_checks_disabled() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"passive_checks_disabled": True})

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["npassive"]


def test_build_service_modes_by_id_out_of_notification_period() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"in_notification_period": False})

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["outofnot"]


def test_build_service_modes_by_id_flapping_is_not_a_mode() -> None:
    # Flapping is shown in the state column instead, not as a mode icon.
    service = ServiceFactory.build(**_NO_MODES | {"is_flapping": True})

    assert build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID) == []


def test_build_service_modes_by_id_all_modes() -> None:
    service = ServiceFactory.build(
        in_downtime=True,
        acknowledged=True,
        notifications_enabled=False,
        num_comments=3,
        active_checks_disabled=True,
        passive_checks_disabled=True,
        in_notification_period=False,
        is_flapping=True,
    )

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == [
        "downtime",
        "ack",
        "notif-disabled",
        "comment",
        "disabled",
        "npassive",
        "outofnot",
    ]


def test_build_service_modes_none() -> None:
    assert build_service_modes(ServiceOverviewFactory.build(**_NO_MODES)) == []


def test_build_service_modes_all_modes() -> None:
    service = ServiceOverviewFactory.build(
        in_downtime=True,
        acknowledged=True,
        notifications_enabled=False,
        num_comments=3,
        active_checks_disabled=True,
        passive_checks_disabled=True,
        in_notification_period=False,
        is_flapping=True,
    )

    assert [mode.icon_name for mode in build_service_modes(service)] == [
        "downtime",
        "ack",
        "notif-disabled",
        "comment",
        "disabled",
        "npassive",
        "outofnot",
    ]


def test_build_service_modes_flapping_is_not_a_mode() -> None:
    # Flapping is shown as its own badge next to the state in the slide-in header instead.
    service = ServiceOverviewFactory.build(**_NO_MODES | {"is_flapping": True})

    assert build_service_modes(service) == []
