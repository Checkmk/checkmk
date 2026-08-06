#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.monitor.services._api._modes import build_service_modes_by_id

from .testlib import ServiceFactory

_HOSTNAME = "web-server-01"
_SITE_ID = "local"


def test_build_service_modes_by_id_none() -> None:
    service = ServiceFactory.build(in_downtime=False, acknowledged=False)
    assert build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID) == []


def test_build_service_modes_by_id_downtime() -> None:
    service = ServiceFactory.build(in_downtime=True, acknowledged=False)
    modes = build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)

    assert [mode.icon_name for mode in modes] == ["downtime"]
    assert modes[0].link.startswith("view.py?")
    assert "downtimes_of_service" in modes[0].link


def test_build_service_modes_by_id_acknowledged() -> None:
    service = ServiceFactory.build(in_downtime=False, acknowledged=True)

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["ack"]


def test_build_service_modes_by_id_downtime_and_acknowledged() -> None:
    service = ServiceFactory.build(in_downtime=True, acknowledged=True)

    assert [
        mode.icon_name
        for mode in build_service_modes_by_id(service, hostname=_HOSTNAME, site_id=_SITE_ID)
    ] == ["downtime", "ack"]
