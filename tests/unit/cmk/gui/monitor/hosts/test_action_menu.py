#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.hosts._api import _action_menu
from cmk.gui.monitor.hosts._api._action_menu import _EXCLUDED_IDENTS, _icon_name, _serialize_entry
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.type_defs import DynamicIconName, DynamicIconWithEmblem, IconNames, StaticIcon
from cmk.gui.views.icon.painter import IconEntry


@pytest.fixture(name="passthrough_macros")
def _passthrough_macros(monkeypatch: pytest.MonkeyPatch) -> None:
    # replace_action_url_macros reads the global user; the mapping logic under test does not
    # depend on macro substitution, so we neutralize it.
    monkeypatch.setattr(_action_menu, "replace_action_url_macros", lambda url, what, row: url)


def test_icon_name_from_static_icon() -> None:
    assert _icon_name(StaticIcon(IconNames.inventory)) == str(IconNames.inventory)


def test_icon_name_from_string() -> None:
    assert _icon_name(DynamicIconName("inventory")) == "inventory"


def test_icon_name_from_dynamic_icon_with_emblem() -> None:
    icon = DynamicIconWithEmblem(icon=DynamicIconName("inventory"), emblem="warning")
    assert _icon_name(icon) == "inventory"


def test_serialize_entry_skips_entries_without_url() -> None:
    entry = IconEntry(sort_index=30, icon_name=StaticIcon(IconNames.inventory), title="Inventory")
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
        icon_name=StaticIcon(IconNames.inventory),
        title="Show HW/SW inventory tree",
        url_spec="view.py?view_name=inv_host&host=web-server-01",
    )
    item = _serialize_entry(entry, {})
    assert item is not None
    assert item.icon_name == str(IconNames.inventory)
    assert item.title == "Show HW/SW inventory tree"
    assert item.url == "view.py?view_name=inv_host&host=web-server-01"
    assert isinstance(item.target, ApiOmitted)


def test_serialize_entry_keeps_target_frame(passthrough_macros: None) -> None:
    entry = IconEntry(
        sort_index=30,
        icon_name=StaticIcon(IconNames.agents),
        title="Download agent output",
        url_spec=("fetch_agent_output.py?host=web-server-01", "_blank"),
    )
    item = _serialize_entry(entry, {})
    assert item is not None
    assert item.url == "fetch_agent_output.py?host=web-server-01"
    assert item.target == "_blank"


def test_setup_actions_are_excluded() -> None:
    assert frozenset({"wato", "rule_editor"}) == _EXCLUDED_IDENTS
