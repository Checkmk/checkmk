#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Protocol


class SupportsJavascript(Protocol):
    def javascript(self, code: str) -> None: ...


def enable_page_menu_entry(writer: SupportsJavascript, name: str) -> None:
    _toggle_page_menu_entry(writer, name, state=True)


def disable_page_menu_entry(writer: SupportsJavascript, name: str) -> None:
    _toggle_page_menu_entry(writer, name, state=False)


def _toggle_page_menu_entry(writer: SupportsJavascript, name: str, state: bool) -> None:
    writer.javascript(f"cmk.page_menu.enable_menu_entry({json.dumps(name)}, {json.dumps(state)})")


def enable_page_menu_entries(writer: SupportsJavascript, css_class: str) -> None:
    toggle_page_menu_entries(writer, css_class, state=True)


def disable_page_menu_entries(writer: SupportsJavascript, css_class: str) -> None:
    toggle_page_menu_entries(writer, css_class, state=False)


def toggle_page_menu_entries(writer: SupportsJavascript, css_class: str, state: bool) -> None:
    writer.javascript(
        f"cmk.page_menu.enable_menu_entries({json.dumps(css_class)}, {json.dumps(state)})"
    )
