#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from html.parser import HTMLParser
from typing import override

import pytest

from cmk.gui.htmllib.html import html
from cmk.gui.monitor.hosts._legacy_view_link import AllHostsLinkButton

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


def _button_payload(button: AllHostsLinkButton, view_name: str) -> dict[str, object] | None:
    with html.output_funnel.plugged():
        button(view_name)
        rendered = html.output_funnel.drain()

    parser = _VueComponentData()
    parser.feed(rendered)
    return parser.payloads[0] if parser.payloads else None


@pytest.mark.usefixtures("request_context")
def test_the_classic_all_hosts_view_offers_the_new_view() -> None:
    payload = _button_payload(AllHostsLinkButton(), "allhosts")

    assert payload is not None
    assert payload["url"] == "monitor_all_hosts.py"


@pytest.mark.usefixtures("request_context")
def test_another_view_is_left_untouched() -> None:
    assert _button_payload(AllHostsLinkButton(), "allservices") is None


@pytest.mark.usefixtures("request_context")
def test_the_button_places_itself_when_no_target_is_configured() -> None:
    payload = _button_payload(AllHostsLinkButton(), "allhosts")

    assert payload is not None
    assert payload["teleport_target"] is None


@pytest.mark.usefixtures("request_context")
def test_the_configured_teleport_target_reaches_the_button() -> None:
    payload = _button_payload(AllHostsLinkButton(SHORTCUTS), "allhosts")

    assert payload is not None
    assert payload["teleport_target"] == SHORTCUTS
