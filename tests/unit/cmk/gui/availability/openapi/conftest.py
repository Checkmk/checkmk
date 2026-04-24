#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.type_defs import AVEntry

BASE = "/NO_SITE/check_mk/api/unstable"
TIME_FROM = "2023-11-14T22:13:20Z"
TIME_UNTIL = "2023-11-15T22:13:20Z"
TIME_PARAMS = f"time_range_from={TIME_FROM}&time_range_until={TIME_UNTIL}"


@pytest.fixture()
def host_av_entry() -> AVEntry:
    return {
        "site": SiteId("NO_SITE"),
        "host": HostName("my-host"),
        "alias": "My Host",
        "service": "",
        "display_name": "",
        "states": {"up": 3600},
        "considered_duration": 3600,
        "total_duration": 3600,
        "statistics": {},
        "groups": None,
        "timeline": [],
    }


@pytest.fixture()
def service_av_entry() -> AVEntry:
    return {
        "site": SiteId("NO_SITE"),
        "host": HostName("my-host"),
        "alias": "My Host",
        "service": "CPU load",
        "display_name": "CPU load",
        "states": {"ok": 3600},
        "considered_duration": 3600,
        "total_duration": 3600,
        "statistics": {},
        "groups": None,
        "timeline": [],
    }
