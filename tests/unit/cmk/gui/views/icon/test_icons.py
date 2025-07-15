#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

import cmk.ccc.version as cmk_version

from cmk.utils import paths

import cmk.gui.permissions
import cmk.gui.views
from cmk.gui.config import active_config
from cmk.gui.type_defs import BuiltinIconVisibility, IconSpec
from cmk.gui.views.icon import (
    Icon,
    icon_and_action_registry,
)
from cmk.gui.views.icon import registry as icon_registry


def test_builtin_icons_and_actions() -> None:
    expected_icons_and_actions = [
        "action_menu",
        "aggregation_checks",
        "aggregations",
        "check_manpage",
        "check_period",
        "crashed_check",
        "custom_action",
        "download_agent_output",
        "download_snmp_walk",
        "icon_image",
        "inventory",
        "inventory_history",
        "logwatch",
        "mkeventd",
        "network_topology",
        "notes",
        "parent_child_topology",
        "perfgraph",
        "prediction",
        "reschedule",
        "rule_editor",
        "stars",
        "status_acknowledged",
        "status_active_checks",
        "status_comments",
        "status_downtimes",
        "status_flapping",
        "status_notification_period",
        "status_notifications_enabled",
        "status_passive_checks",
        "status_service_period",
        "status_stale",
        "wato",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected_icons_and_actions += [
            "agent_deployment",
            "deployment_status",
            "status_shadow",
            "ntop_host",
            "robotmk_html_log",
        ]

    cmk.gui.views.register_legacy_icons()
    builtin_icons = sorted(icon_and_action_registry.keys())
    assert builtin_icons == sorted(expected_icons_and_actions)


def test_legacy_icon_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    icon: dict[str, Any] = {
        "columns": ["column"],
        "host_columns": ["hcol"],
        "service_columns": ["scol"],
        "paint": lambda what, row, tags, custom_vars: "bla",
        "sort_index": 10,
        "toplevel": True,
    }
    monkeypatch.setattr(
        cmk.gui.views, "icon_and_action_registry", registry := icon_registry.IconRegistry()
    )
    monkeypatch.setitem(cmk.gui.views.multisite_icons_and_actions, "legacy", icon)
    cmk.gui.views.register_legacy_icons()

    registered_icon = registry["legacy"]
    assert registered_icon.columns == icon["columns"]
    assert registered_icon.host_columns == icon["host_columns"]
    assert registered_icon.service_columns == icon["service_columns"]
    assert registered_icon.render("host", {}, [], {}) == icon["paint"]("host", {}, [], {})
    assert registered_icon.toplevel is True
    assert registered_icon.sort_index == 10


def test_legacy_icon_plugin_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    icon = {
        "columns": ["column"],
        "host_columns": ["hcol"],
        "service_columns": ["scol"],
        "paint": lambda: "bla",
    }
    monkeypatch.setattr(
        cmk.gui.views, "icon_and_action_registry", registry := icon_registry.IconRegistry()
    )
    monkeypatch.setitem(cmk.gui.views.multisite_icons_and_actions, "legacy", icon)
    cmk.gui.views.register_legacy_icons()

    registered_icon = registry["legacy"]
    assert registered_icon.toplevel is False
    assert registered_icon.sort_index == 30


def test_register_icon_plugin_with_default_registry_works(monkeypatch: pytest.MonkeyPatch) -> None:
    def render(what, row, tags, custom_vars):
        return "agents", "Title", "url"

    TestIcon = Icon(
        ident="test_icon",
        title="Test icon",
        sort_index=50,
        render=render,
    )

    monkeypatch.setattr(
        icon_registry, "icon_and_action_registry", registry := icon_registry.IconRegistry()
    )
    registry.register(TestIcon)

    assert "test_icon" in icon_registry.icon_and_action_registry


@pytest.mark.usefixtures("load_config")
def test_config_icon_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(icon_registry, "icon_and_action_registry", icon_registry.IconRegistry())

    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "user_icons_and_actions",
            {
                "config_icon": IconSpec(
                    {
                        "icon": "icon",
                        "title": "Config Icon",
                        "sort_index": 10,
                        "toplevel": True,
                    }
                ),
            },
        )
        assert "config_icon" in icon_registry.all_icons()


@pytest.mark.usefixtures("load_config")
def test_config_override_builtin_icons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        icon_registry, "icon_and_action_registry", registry := icon_registry.IconRegistry()
    )

    def render(what, row, tags, custom_vars):
        return "agents", "Title", "url"

    TestIcon = Icon(ident="test_icon", title="Test icon", sort_index=50, render=render)

    registry.register(TestIcon)

    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "builtin_icon_visibility",
            {
                "test_icon": BuiltinIconVisibility(
                    {
                        "toplevel": True,
                    }
                ),
            },
        )
        assert icon_registry.all_icons()["test_icon"].toplevel is True
