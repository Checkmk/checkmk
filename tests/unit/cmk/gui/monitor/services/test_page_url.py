#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from urllib.parse import parse_qs, urlsplit

from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.monitor.services._api._filters import ServiceStringCondition
from cmk.gui.monitor.services.page_url import (
    all_services_url,
    host_service_panel_url,
    host_services_url,
)


def test_host_services_url_names_the_host_and_its_site() -> None:
    parts = urlsplit(
        host_services_url(Request(create_environ()), host_name="web 01&x", site_id="remote")
    )

    assert parts.path == "monitor_host_services.py"
    assert parse_qs(parts.query) == {"host": ["web 01&x"], "site": ["remote"]}


def test_host_services_url_opens_the_host_panel_by_its_fragment() -> None:
    parts = urlsplit(
        host_services_url(
            Request(create_environ()), host_name="web 01&x", site_id="remote", open_host_panel=True
        )
    )

    assert parse_qs(parts.query) == {"host": ["web 01&x"], "site": ["remote"]}
    assert parse_qs(parts.fragment) == {"host": ["web 01&x"], "site": ["remote"]}


def test_host_services_url_carries_the_filter_and_names_the_unapplied_filters() -> None:
    parts = urlsplit(
        host_services_url(
            Request(create_environ()),
            host_name="web-01",
            site_id="remote",
            filter_node=ServiceStringCondition(
                type="condition", field="name", op="contains", value="CPU"
            ),
            unapplied=["hostregex"],
        )
    )

    query = parse_qs(parts.query)
    assert {**query, "filter": [json.loads(value) for value in query["filter"]]} == {
        "host": ["web-01"],
        "site": ["remote"],
        "filter": [{"type": "condition", "field": "name", "op": "contains", "value": "CPU"}],
        "unapplied": ["hostregex"],
    }


def test_all_services_url_without_a_filter_names_the_unapplied_filters() -> None:
    url = all_services_url(Request(create_environ()), unapplied=["hoststate"])

    assert url == "monitor_all_services.py?unapplied=hoststate"


def test_host_service_panel_url_opens_the_service_panel_on_its_host() -> None:
    parts = urlsplit(
        host_service_panel_url(
            Request(create_environ()), host_name="web 01&x", site_id="remote", service="CPU & load"
        )
    )

    assert parts.path == "monitor_host_services.py"
    assert parse_qs(parts.query) == {"host": ["web 01&x"], "site": ["remote"]}
    assert parse_qs(parts.fragment) == {"service": ["CPU & load"]}
