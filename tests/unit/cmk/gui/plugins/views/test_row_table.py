#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.data_source import RowTableLivestatus
from cmk.gui.view import View
from cmk.gui.views.store import multisite_builtin_views
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("request_context")
def test_row_table_object(mock_livestatus: MockLiveStatusConnection) -> None:
    live = mock_livestatus
    live.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "alias": "heute",
                "host_state": 0,
                "host_has_been_checked": False,
            }
        ],
    )
    live.expect_query(
        "GET hosts\nColumns: host_has_been_checked host_state name\nFilter: name = heute"
    )

    view_name = "allhosts"
    view_spec = multisite_builtin_views[view_name].copy()
    view_spec["painters"] = []
    view_spec["group_painters"] = []
    view_spec["sorters"] = []
    view_spec["context"] = {
        "host": {"host": "heute"},
        "service": {},
    }
    view = View(view_name, view_spec, view_spec["context"])
    rt = RowTableLivestatus("hosts")

    # @Christoph: Test geht kaputt wenn headers="Filter: host_name = heute"
    # der host_ prefix, passend angepasst generiert eine extra query?
    with live(expect_status_query=True):
        rt.query(
            view.datasource,
            view.row_cells,
            columns=["name"],
            context=view.context,
            headers="Filter: name = heute",
            only_sites=None,
            limit=None,
            all_active_filters=[],
        )
