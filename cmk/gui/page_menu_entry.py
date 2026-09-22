#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Protocol

from cmk.gui.htmllib.generator import KnownTSFunction, TSFunctionArguments


class SupportsCallTSFunction(Protocol):
    def call_ts_function(
        self,
        *,
        container: str = "div",
        function_name: KnownTSFunction,
        arguments: TSFunctionArguments | None = None,
    ) -> None: ...


def enable_page_menu_entry(writer: SupportsCallTSFunction, name: str) -> None:
    _toggle_page_menu_entry(writer, name, state=True)


def disable_page_menu_entry(writer: SupportsCallTSFunction, name: str) -> None:
    _toggle_page_menu_entry(writer, name, state=False)


def _toggle_page_menu_entry(writer: SupportsCallTSFunction, name: str, state: bool) -> None:
    writer.call_ts_function(
        function_name="enable_menu_entry", arguments={"id": name, "enabled": state}
    )


def enable_page_menu_entries(writer: SupportsCallTSFunction, css_class: str) -> None:
    toggle_page_menu_entries(writer, css_class, state=True)


def disable_page_menu_entries(writer: SupportsCallTSFunction, css_class: str) -> None:
    toggle_page_menu_entries(writer, css_class, state=False)


def toggle_page_menu_entries(writer: SupportsCallTSFunction, css_class: str, state: bool) -> None:
    writer.call_ts_function(
        function_name="enable_menu_entries", arguments={"css_class": css_class, "enabled": state}
    )
