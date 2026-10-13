#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.views.command import command_group_registry, command_registry
from cmk.gui.views.exporter import exporter_registry
from cmk.gui.views.layout import layout_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_layouts() -> None:
    expected = [
        "boxed",
        "boxed_graph",
        "dataset",
        "matrix",
        "mobiledataset",
        "mobilelist",
        "mobiletable",
        "table",
        "tiled",
    ]

    names = layout_registry.keys()
    assert sorted(expected) == sorted(names)


@pytest.mark.usefixtures("load_gui_plugins")
def test_layout_properties() -> None:
    expected = {
        "boxed": {"checkboxes": True, "title": "Balanced boxes"},
        "boxed_graph": {"checkboxes": True, "title": "Balanced graph boxes"},
        "dataset": {"checkboxes": False, "title": "Single dataset"},
        "matrix": {
            "checkboxes": False,
            "has_csv_export": True,
            "options": ["matrix_omit_uniform"],
            "title": "Matrix",
        },
        "mobiledataset": {"checkboxes": False, "title": "Mobile: Dataset"},
        "mobilelist": {"checkboxes": False, "title": "Mobile: List"},
        "mobiletable": {"checkboxes": False, "title": "Mobile: Table"},
        "table": {"checkboxes": True, "title": "Table"},
        "tiled": {"checkboxes": True, "title": "Tiles"},
    }

    for ident, spec in expected.items():
        plugin = layout_registry[ident]()
        assert isinstance(plugin.title, str)
        assert spec["title"] == plugin.title
        assert spec["checkboxes"] == plugin.can_display_checkboxes
        assert spec.get("has_csv_export", False) == plugin.has_individual_csv_export


@pytest.mark.usefixtures("load_gui_plugins")
def test_get_layout_choices() -> None:
    choices = layout_registry.get_choices()
    assert sorted(choices) == sorted(
        [
            ("matrix", "Matrix"),
            ("boxed_graph", "Balanced graph boxes"),
            ("dataset", "Single dataset"),
            ("tiled", "Tiles"),
            ("table", "Table"),
            ("boxed", "Balanced boxes"),
            ("mobiledataset", "Mobile: Dataset"),
            ("mobiletable", "Mobile: Table"),
            ("mobilelist", "Mobile: List"),
        ]
    )


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_exporters() -> None:
    expected = [
        "csv",
        "csv_export",
        "json",
        "json_export",
        "jsonp",
        "python",
        "python-raw",
    ]
    names = exporter_registry.keys()
    assert sorted(expected) == sorted(names)


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_command_groups() -> None:
    expected = [
        "acknowledge",
        "aggregations",
        "downtimes",
        "fake_check",
        "various",
    ]

    names = command_group_registry.keys()
    assert sorted(expected) == sorted(names)


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_commands() -> None:
    expected: dict[str, dict[str, object]] = {
        "acknowledge": {
            "group": "acknowledge",
            "permission": "action.acknowledge",
            "tables": ["host", "service", "aggr"],
            "title": "Acknowledge problems",
        },
        "freeze_aggregation": {
            "group": "aggregations",
            "permission": "action.aggregation_freeze",
            "tables": ["aggr"],
            "title": "Freeze aggregations",
        },
        "ec_custom_actions": {
            "permission": "mkeventd.actions",
            "tables": ["event"],
            "title": "Custom action",
        },
        "remove_acknowledgments": {
            "group": "acknowledge",
            "permission": "action.acknowledge",
            "tables": ["host", "service", "aggr"],
            "title": "Remove acknowledgments",
        },
        "remove_comments": {
            "permission": "action.addcomment",
            "tables": ["comment"],
            "title": "Delete comments",
        },
        "remove_downtimes_hosts_services": {
            "permission": "action.downtimes",
            "tables": ["host", "service", "aggr"],
            "title": "Remove downtimes",
        },
        "remove_downtimes": {
            "permission": "action.downtimes",
            "tables": ["downtime"],
            "title": "Remove downtimes",
        },
        "schedule_downtimes": {
            "permission": "action.downtimes",
            "tables": ["host", "service", "aggr"],
            "title": "Schedule downtimes",
        },
        "ec_archive_events_of_host": {
            "permission": "mkeventd.archive_events_of_hosts",
            "tables": ["service"],
            "title": "Archive events of hosts",
        },
        "ec_change_state": {
            "permission": "mkeventd.changestate",
            "tables": ["event"],
            "title": "Change state",
        },
        "clear_modified_attributes": {
            "permission": "action.clearmodattr",
            "tables": ["host", "service"],
            "title": "Reset modified attributes",
        },
        "send_custom_notification": {
            "permission": "action.customnotification",
            "tables": ["host", "service"],
            "title": "Send custom notification",
        },
        "ec_archive_event": {
            "permission": "mkeventd.delete",
            "tables": ["event"],
            "title": "Archive event",
        },
        "add_comment": {
            "permission": "action.addcomment",
            "tables": ["host", "service"],
            "title": "Add comment",
        },
        "toggle_passive_checks": {
            "permission": "action.enablechecks",
            "tables": ["host", "service"],
            "title": "Enable/disable passive checks",
        },
        "toggle_active_checks": {
            "permission": "action.enablechecks",
            "tables": ["host", "service"],
            "title": "Enable/disable active checks",
        },
        "fake_check_result": {
            "group": "fake_check",
            "permission": "action.fakechecks",
            "tables": ["host", "service"],
            "title": "Fake check results",
        },
        "notifications": {
            "permission": "action.notifications",
            "tables": ["host", "service"],
            "title": "Enable/disable notifications",
        },
        "reschedule": {
            "permission": "action.reschedule",
            "row_stats": True,
            "tables": ["host", "service"],
            "title": "Reschedule active checks",
        },
        "ec_update_event": {
            "permission": "mkeventd.update",
            "tables": ["event"],
            "title": "Update & acknowledge",
        },
        "delete_crash_reports": {
            "permission": "action.delete_crash_report",
            "tables": ["crash"],
            "title": "Delete crash reports",
        },
    }

    names = command_registry.keys()
    assert sorted(expected.keys()) == sorted(names)

    for cmd in command_registry.values():
        cmd_spec = expected[cmd.ident]
        assert cmd.title == cmd_spec["title"]
        assert cmd.tables == cmd_spec["tables"], cmd.ident
        assert cmd.permission.name == cmd_spec["permission"]
