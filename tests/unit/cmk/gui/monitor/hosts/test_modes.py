#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest

from cmk.gui.monitor.hosts._api._modes import build_host_modes

from .testlib import HostFactory, login_with

_ALL_HOSTS_PERMISSION = "view.allhosts"


@pytest.fixture(name="may_see_all_hosts")
def _may_see_all_hosts() -> Iterator[None]:
    with login_with({_ALL_HOSTS_PERMISSION: True}):
        yield


pytestmark = pytest.mark.usefixtures("request_context", "may_see_all_hosts")


# The factory randomises every field, so a test that asserts on one mode has to pin all the
# others to the value that keeps their icon away.
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
}


def test_build_host_modes_none() -> None:
    assert build_host_modes(HostFactory.build(**_NO_MODES)) == []


def test_build_host_modes_downtime() -> None:
    host = HostFactory.build(**_NO_MODES | {"in_downtime": True})
    modes = build_host_modes(host)

    assert [mode.icon_name for mode in modes] == ["downtime"]
    assert modes[0].link.startswith("view.py?")
    assert "downtimes_of_host" in modes[0].link


def test_build_host_modes_acknowledged() -> None:
    host = HostFactory.build(**_NO_MODES | {"acknowledged": True})

    assert [mode.icon_name for mode in build_host_modes(host)] == ["ack"]


def test_build_host_modes_notifications_disabled() -> None:
    host = HostFactory.build(**_NO_MODES | {"notifications_enabled": False})

    assert [mode.icon_name for mode in build_host_modes(host)] == ["notif-disabled"]


def test_build_host_modes_comments() -> None:
    host = HostFactory.build(**_NO_MODES | {"num_comments": 2})
    modes = build_host_modes(host)

    assert [mode.icon_name for mode in modes] == ["comment"]
    assert "comments_of_host" in modes[0].link
    assert modes[0].title == "This host has 2 comments"


def test_build_host_modes_active_checks_disabled() -> None:
    host = HostFactory.build(**_NO_MODES | {"active_checks_disabled": True})

    assert [mode.icon_name for mode in build_host_modes(host)] == ["disabled"]


def test_build_host_modes_passive_checks_disabled() -> None:
    host = HostFactory.build(**_NO_MODES | {"passive_checks_disabled": True})

    assert [mode.icon_name for mode in build_host_modes(host)] == ["npassive"]


def test_build_host_modes_out_of_notification_period() -> None:
    host = HostFactory.build(**_NO_MODES | {"in_notification_period": False})

    assert [mode.icon_name for mode in build_host_modes(host)] == ["outofnot"]


def test_build_host_modes_out_of_service_period() -> None:
    host = HostFactory.build(**_NO_MODES | {"in_service_period": False})

    assert [mode.icon_name for mode in build_host_modes(host)] == ["outof-serviceperiod"]


def test_build_host_modes_not_currently_checked() -> None:
    host = HostFactory.build(**_NO_MODES | {"in_check_period": False})

    assert [mode.icon_name for mode in build_host_modes(host)] == ["pause"]


def test_build_host_modes_all_modes() -> None:
    host = HostFactory.build(
        in_downtime=True,
        acknowledged=True,
        notifications_enabled=False,
        num_comments=1,
        active_checks_disabled=True,
        passive_checks_disabled=True,
        in_notification_period=False,
        in_service_period=False,
        in_check_period=False,
    )

    assert [mode.icon_name for mode in build_host_modes(host)] == [
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


def test_build_host_modes_state_icons_open_the_host_panel() -> None:
    host = HostFactory.build(
        name="web-server-01",
        site_id="local",
        in_downtime=False,
        num_comments=0,
        acknowledged=True,
        notifications_enabled=False,
        active_checks_disabled=True,
        passive_checks_disabled=True,
        in_notification_period=False,
        in_service_period=False,
        in_check_period=False,
    )

    assert {mode.link for mode in build_host_modes(host)} == {
        "monitor_all_hosts.py#host=web-server-01&site=local"
    }


def test_build_host_modes_state_icons_fall_back_without_the_listing_permission() -> None:
    host = HostFactory.build(
        **_NO_MODES | {"name": "web-server-01", "site_id": "local", "acknowledged": True}
    )

    with login_with({_ALL_HOSTS_PERMISSION: False}):
        modes = build_host_modes(host)

    assert [mode.link for mode in modes] == [
        "view.py?view_name=hoststatus&site=local&host=web-server-01"
    ]
