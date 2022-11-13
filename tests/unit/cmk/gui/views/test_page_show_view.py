#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

import pytest

import cmk.utils.version as cmk_version

from cmk.gui.plugins.visuals.utils import Filter
from cmk.gui.type_defs import PainterSpec
from cmk.gui.view import View
from cmk.gui.views.page_show_view import _get_needed_join_columns, _get_needed_regular_columns


def test_get_needed_regular_columns(view: View) -> None:
    class SomeFilter(Filter):
        def display(self, value):
            return

        def columns_for_filter_table(self, context):
            return ["some_column"]

    columns = _get_needed_regular_columns(
        [
            SomeFilter(
                ident="some_filter",
                title="Some filter",
                sort_index=1,
                info="info",
                htmlvars=[],
                link_columns=[],
            )
        ],
        view,
    )
    assert sorted(columns) == sorted(
        [
            "host_accept_passive_checks",
            "host_acknowledged",
            "host_action_url_expanded",
            "host_active_checks_enabled",
            "host_address",
            "host_check_command",
            "host_check_type",
            "host_comments_with_extra_info",
            "host_custom_variable_names",
            "host_custom_variable_values",
            "host_downtimes",
            "host_downtimes_with_extra_info",
            "host_filename",
            "host_has_been_checked",
            "host_icon_image",
            "host_in_check_period",
            "host_in_notification_period",
            "host_in_service_period",
            "host_is_flapping",
            "host_modified_attributes_list",
            "host_name",
            "host_notes_url_expanded",
            "host_notifications_enabled",
            "host_num_services_crit",
            "host_num_services_ok",
            "host_num_services_pending",
            "host_num_services_unknown",
            "host_num_services_warn",
            "host_perf_data",
            "host_pnpgraph_present",
            "host_scheduled_downtime_depth",
            "host_staleness",
            "host_state",
            "some_column",
        ]
    )


@pytest.mark.usefixtures("load_config")
def test_get_needed_join_columns(view: View) -> None:
    view_spec = copy.deepcopy(view.spec)
    view_spec["painters"] = [
        *view_spec["painters"],
        PainterSpec(name="service_description", join_index="CPU load"),
    ]
    view = View(view.name, view_spec, view_spec.get("context", {}))

    columns = _get_needed_join_columns(view.join_cells, view.sorters)

    expected_columns = [
        "host_name",
        "service_description",
    ]

    if cmk_version.is_managed_edition():
        expected_columns += [
            "host_custom_variable_names",
            "host_custom_variable_values",
        ]

    assert sorted(columns) == sorted(expected_columns)
