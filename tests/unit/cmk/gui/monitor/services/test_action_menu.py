#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.services._api import _action_menu
from cmk.gui.monitor.services._api._action_menu import (
    _EXCLUDED_IDENTS,
    _icon_name,
    _serialize_entry,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.type_defs import DynamicIconName, DynamicIconWithEmblem, IconNames, Row, StaticIcon
from cmk.gui.views.icon.entries import IconEntry


@pytest.fixture(name="passthrough_macros")
def _passthrough_macros(monkeypatch: pytest.MonkeyPatch) -> None:
    # replace_action_url_macros reads the global user; the mapping logic under test does not
    # depend on macro substitution, so we neutralize it.
    monkeypatch.setattr(_action_menu, "replace_action_url_macros", lambda url, what, row: url)


def test_icon_name_from_static_icon() -> None:
    assert _icon_name(StaticIcon(IconNames.logwatch)) == str(IconNames.logwatch)


def test_icon_name_from_string() -> None:
    assert _icon_name(DynamicIconName("logwatch")) == "logwatch"


def test_icon_name_from_dynamic_icon_with_emblem() -> None:
    icon = DynamicIconWithEmblem(icon=DynamicIconName("logwatch"), emblem="warning")
    assert _icon_name(icon) == "logwatch"


def test_serialize_entry_skips_entries_without_url() -> None:
    entry = IconEntry(sort_index=30, icon_name=StaticIcon(IconNames.logwatch), title="Log file")
    assert _serialize_entry(entry, {}) is None


def test_serialize_entry_skips_onclick_commands(passthrough_macros: None) -> None:
    entry = IconEntry(
        sort_index=30,
        icon_name=StaticIcon(IconNames.reload),
        title="Reschedule",
        url_spec="onclick:reschedule();",
    )
    assert _serialize_entry(entry, {}) is None


def test_serialize_entry_maps_link(passthrough_macros: None) -> None:
    entry = IconEntry(
        sort_index=30,
        icon_name=StaticIcon(IconNames.logwatch),
        title="Open log file viewer",
        url_spec="view.py?view_name=logwatch&host=web-server-01",
    )
    item = _serialize_entry(entry, {})
    assert item is not None
    assert item.icon_name == str(IconNames.logwatch)
    assert item.title == "Open log file viewer"
    assert item.url == "view.py?view_name=logwatch&host=web-server-01"
    assert isinstance(item.target, ApiOmitted)


def test_serialize_entry_keeps_target_frame(passthrough_macros: None) -> None:
    entry = IconEntry(
        sort_index=30,
        icon_name=StaticIcon(IconNames.graph),
        title="Open graphs",
        url_spec=("view.py?view_name=service_graphs&host=web-server-01", "_blank"),
    )
    item = _serialize_entry(entry, {})
    assert item is not None
    assert item.url == "view.py?view_name=service_graphs&host=web-server-01"
    assert item.target == "_blank"


def test_serialize_entry_substitutes_the_service_macros(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def record_what(url: str, what: str, row: Row) -> str:
        seen.append(what)
        return url

    monkeypatch.setattr(_action_menu, "replace_action_url_macros", record_what)

    _serialize_entry(
        IconEntry(
            sort_index=30,
            icon_name=StaticIcon(IconNames.logwatch),
            title="Open log file viewer",
            url_spec="view.py?view_name=logwatch",
        ),
        {},
    )

    assert seen == ["service"]


def test_the_inline_parameters_button_is_excluded() -> None:
    assert frozenset({"rule_editor"}) == _EXCLUDED_IDENTS
