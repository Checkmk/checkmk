#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from cmk.gui.monitor.services._api._modes import (
    build_host_modes,
    build_service_modes,
    build_service_modes_by_id,
)
from cmk.gui.monitor.services._models import ServiceState

from .testlib import login_with, ServiceFactory, ServiceOverviewFactory

_ALL_HOSTS_PERMISSION = "view.allhosts"

_HOST_SERVICES_PERMISSION = "view.host"

_CRASH_REPORTS_PERMISSION = "general.see_crash_reports"


@pytest.fixture(name="may_see_the_listings")
def _may_see_the_listings() -> Iterator[None]:
    with login_with(
        {
            _ALL_HOSTS_PERMISSION: True,
            _HOST_SERVICES_PERMISSION: True,
            _CRASH_REPORTS_PERMISSION: True,
        }
    ):
        yield


pytestmark = pytest.mark.usefixtures("request_context", "may_see_the_listings")


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
    "in_service_period": True,
    "in_check_period": True,
    "is_flapping": False,
    # A crash is read off the state and the output, so a plain OK keeps the crash icon away.
    "state": ServiceState.OK,
    "summary": "OK - everything is fine",
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


def test_build_service_modes_by_id_out_of_service_period() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"in_service_period": False})

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["outof-serviceperiod"]


def test_build_service_modes_by_id_not_currently_checked() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"in_check_period": False})

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["pause"]


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
        in_service_period=False,
        in_check_period=False,
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
        "outof-serviceperiod",
        "pause",
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
        in_service_period=False,
        in_check_period=False,
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
        "outof-serviceperiod",
        "pause",
    ]


def test_build_service_modes_flapping_is_not_a_mode() -> None:
    # Flapping is shown as its own badge next to the state in the slide-in header instead.
    service = ServiceOverviewFactory.build(**_NO_MODES | {"is_flapping": True})

    assert build_service_modes(service) == []


_CRASHED_OUTPUT = "UNKNOWN - check failed - please submit a crash report! (Crash-ID: abc-123)"


def test_build_service_modes_by_id_crashed_check_links_to_the_dump() -> None:
    service = ServiceFactory.build(
        **_NO_MODES | {"state": ServiceState.UNKNOWN, "summary": _CRASHED_OUTPUT}
    )
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["crash"]
    assert modes[0].link == "crash.py?site=local&crash_id=abc-123"


def test_build_service_modes_by_id_crashed_check_without_a_dump_links_nowhere() -> None:
    service = ServiceFactory.build(
        **_NO_MODES
        | {
            "state": ServiceState.UNKNOWN,
            "summary": "UNKNOWN - check failed - please submit a crash report!",
        }
    )
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["crash"]
    assert modes[0].link == ""


def test_build_service_modes_by_id_crashed_check_withholds_the_dump_without_the_permission() -> (
    None
):
    service = ServiceFactory.build(
        **_NO_MODES | {"state": ServiceState.UNKNOWN, "summary": _CRASHED_OUTPUT}
    )

    with login_with({_CRASH_REPORTS_PERMISSION: False}):
        modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["crash"]
    assert modes[0].link == ""


def test_build_service_modes_by_id_an_unknown_service_did_not_crash() -> None:
    # UNKNOWN on its own is an ordinary result; only the marker cmk.base appends means a crash.
    service = ServiceFactory.build(
        **_NO_MODES | {"state": ServiceState.UNKNOWN, "summary": "UNKNOWN - cannot reach the API"}
    )

    assert build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID) == []


def test_build_service_modes_by_id_state_icons_open_the_service_panel() -> None:
    service = ServiceFactory.build(
        **_NO_MODES
        | {
            "name": "CPU load",
            "acknowledged": True,
            "notifications_enabled": False,
            "active_checks_disabled": True,
            "passive_checks_disabled": True,
            "in_notification_period": False,
            "in_service_period": False,
            "in_check_period": False,
        }
    )

    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert {mode.link for mode in modes} == {
        "monitor_host_services.py?host=web-server-01&site=local#service=CPU+load"
    }


def test_build_service_modes_by_id_state_icons_fall_back_without_the_listing_permission() -> None:
    service = ServiceFactory.build(**_NO_MODES | {"name": "CPU load", "acknowledged": True})

    with login_with({_HOST_SERVICES_PERMISSION: False}):
        modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.link for mode in modes] == [
        "view.py?view_name=service&site=local&host=web-server-01&service=CPU+load"
    ]


def test_build_host_modes_acknowledged_opens_the_host_panel() -> None:
    service = ServiceOverviewFactory.build(
        host_name=_HOSTNAME,
        site_id=_SITE_ID,
        host_in_downtime=False,
        host_acknowledged=True,
    )

    assert [mode.link for mode in build_host_modes(service)] == [
        "monitor_all_hosts.py#host=web-server-01&site=local"
    ]


def test_build_host_modes_fall_back_without_the_all_hosts_permission() -> None:
    service = ServiceOverviewFactory.build(
        host_name=_HOSTNAME,
        site_id=_SITE_ID,
        host_in_downtime=False,
        host_acknowledged=True,
    )

    with login_with({_ALL_HOSTS_PERMISSION: False}):
        modes = build_host_modes(service)

    assert [mode.link for mode in modes] == [
        "view.py?view_name=hoststatus&site=local&host=web-server-01"
    ]
