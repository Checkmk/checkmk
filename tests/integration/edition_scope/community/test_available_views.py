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
    assert sorted(command_registry) == [
        "acknowledge",
        "add_comment",
        "clear_modified_attributes",
        "delete_crash_reports",
        "ec_archive_event",
        "ec_archive_events_of_host",
        "ec_change_state",
        "ec_custom_actions",
        "ec_update_event",
        "fake_check_result",
        "freeze_aggregation",
        "notifications",
        "remove_acknowledgments",
        "remove_comments",
        "remove_downtimes",
        "remove_downtimes_hosts_services",
        "reschedule",
        "schedule_downtimes",
        "send_custom_notification",
        "toggle_active_checks",
        "toggle_passive_checks",
    ]
