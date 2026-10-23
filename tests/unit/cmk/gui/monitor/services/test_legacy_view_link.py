#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from html.parser import HTMLParser
from typing import override

import pytest

from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.monitor.services._legacy_view_link import HostServicesLinkButton

SHORTCUTS = "#page_menu_bar .shortcuts"


class _VueComponentData(HTMLParser):
    """Collects the payload every ``cmk-...`` web component was handed."""

    def __init__(self) -> None:
        super().__init__()
        self.payloads: list[dict[str, object]] = []

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not tag.startswith("cmk-"):
            return
        for name, value in attrs:
            if name == "data" and value is not None:
                self.payloads.append(json.loads(value))


def _button_payload(button: HostServicesLinkButton, view_name: str) -> dict[str, object] | None:
    with html.output_funnel.plugged():
        button(view_name)
        rendered = html.output_funnel.drain()

    parser = _VueComponentData()
    parser.feed(rendered)
    return parser.payloads[0] if parser.payloads else None


@pytest.fixture(name="host_in_request")
def fixture_host_in_request() -> None:
    request.set_var("host", "heute")
    request.set_var("site", "heute")


@pytest.mark.usefixtures("request_context", "host_in_request")
def test_the_classic_services_view_offers_the_new_view() -> None:
    payload = _button_payload(HostServicesLinkButton(), "host")

    assert payload is not None
    assert payload["url"] == "monitor_host_services.py?host=heute&site=heute"


@pytest.mark.usefixtures("request_context", "host_in_request")
def test_another_view_is_left_untouched() -> None:
    assert _button_payload(HostServicesLinkButton(), "allhosts") is None


@pytest.mark.usefixtures("request_context")
def test_a_view_without_a_host_is_left_untouched() -> None:
    request.set_var("site", "heute")

    assert _button_payload(HostServicesLinkButton(), "host") is None


@pytest.mark.usefixtures("request_context")
def test_a_view_without_a_site_is_left_untouched() -> None:
    request.set_var("host", "heute")

    assert _button_payload(HostServicesLinkButton(), "host") is None


@pytest.mark.usefixtures("request_context", "host_in_request")
def test_the_button_places_itself_when_no_target_is_configured() -> None:
    payload = _button_payload(HostServicesLinkButton(), "host")

    assert payload is not None
    assert payload["teleport_target"] is None


@pytest.mark.usefixtures("request_context", "host_in_request")
def test_the_configured_teleport_target_reaches_the_button() -> None:
    payload = _button_payload(HostServicesLinkButton(SHORTCUTS), "host")

    assert payload is not None
    assert payload["teleport_target"] == SHORTCUTS
