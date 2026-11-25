#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib.parse import parse_qs, urlsplit

from werkzeug.test import create_environ

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.http import Request
from cmk.gui.monitor.router import monitor_result_url
from cmk.gui.search.livestatus_links import (
    ResultGroup,
    ResultHost,
    ResultService,
    ResultTarget,
)


def _url(target: ResultTarget) -> str | None:
    return monitor_result_url(Request(create_environ()), target)


def test_a_host_opens_its_services_with_the_host_panel() -> None:
    url = _url(ResultHost(site_id=SiteId("remote"), host_name=HostName("web01")))

    assert url is not None
    parts = urlsplit(url)
    assert parts.path == "monitor_host_services.py"
    assert parse_qs(parts.query) == {"host": ["web01"], "site": ["remote"]}
    assert parse_qs(parts.fragment) == {"host": ["web01"], "site": ["remote"]}


def test_a_service_opens_its_host_with_the_service_panel() -> None:
    url = _url(
        ResultService(site_id=SiteId("remote"), host_name=HostName("web01"), service="CPU load")
    )

    assert url is not None
    parts = urlsplit(url)
    assert parts.path == "monitor_host_services.py"
    assert parse_qs(parts.query) == {"host": ["web01"], "site": ["remote"]}
    assert parse_qs(parts.fragment) == {"service": ["CPU load"]}


def test_a_group_has_no_monitoring_page() -> None:
    assert _url(ResultGroup(kind="host", name="linux")) is None
