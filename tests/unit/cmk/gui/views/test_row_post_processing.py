#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.version as cmk_version

from cmk.utils import paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.structured_data import ImmutableTree

from cmk.gui.type_defs import Rows
from cmk.gui.view import View
from cmk.gui.views.row_post_processing import post_process_rows, row_post_processor_registry
from cmk.gui.views.store import multisite_builtin_views


def test_post_processor_registrations() -> None:
    names = [f.__name__ for f in row_post_processor_registry.values()]
    expected = [
        "inventory_row_post_processor",
        "join_service_row_post_processor",
    ]
    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected.append("sla_row_post_processor")
    assert sorted(names) == sorted(expected)


def test_post_process_rows_not_failing_on_empty_rows(view: View) -> None:
    rows: Rows = []
    post_process_rows(view, [], rows)
    assert not rows


def test_post_process_rows_adds_inventory_data(
    mock_livestatus: MockLiveStatusConnection, request_context: None
) -> None:
    inv_view = inventory_view()
    host_row = {"site": "ding", "host_name": "dong"}
    rows: Rows = [host_row]
    mock_livestatus.expect_query(
        "GET services\nColumns: host_has_been_checked host_name host_state service_check_command "
        "service_description service_perf_data service_plugin_output service_pnpgraph_present "
        "service_staleness service_state\nFilter: service_description = CPU load\n"
        "Filter: service_description = CPU utilization\nOr: 2"
    )
    with mock_livestatus():
        post_process_rows(inv_view, [], rows)
    assert rows == [host_row]
    assert isinstance(host_row["host_inventory"], ImmutableTree)


def inventory_view() -> View:
    view_spec = multisite_builtin_views["inv_hosts_cpu"].copy()
    return View("inv_hosts_cpu", view_spec, view_spec.get("context", {}))
