#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

import pytest

from cmk.gui.config import Config
from cmk.gui.type_defs import ColumnSpec, Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views._join_service_rows import (
    _get_needed_join_columns,
    join_service_row_post_processor,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.web.utils.request_cache import RequestCache
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


def _with_painters(view: View, painters: list[ColumnSpec]) -> View:
    view_spec = copy.deepcopy(view.spec)
    view_spec["painters"] = painters
    return View(
        view.name,
        view_spec,
        view_spec.get("context", {}),
        make_painter_context(UserPermissions({}, {}, {}, [])),
        RequestCache(Config()),
    )


@pytest.mark.usefixtures("load_config")
def test_get_needed_join_columns(view: View) -> None:
    view = _with_painters(
        view,
        [*view.spec["painters"], ColumnSpec(name="service_description", join_value="CPU load")],
    )

    columns = _get_needed_join_columns(view.join_cells, view.sorters)

    expected_columns = [
        "host_name",
        "service_description",
    ]

    assert sorted(columns) == sorted(expected_columns)


SERVICES = [
    {
        "host_name": "alpha",
        "host_state": 0,
        "host_has_been_checked": 1,
        "service_description": description,
        "service_state": state,
        "service_has_been_checked": 1,
    }
    for description, state in (("CPU load", 2), ("Memory", 0))
]


@pytest.mark.parametrize(
    "join_value, expected_filter",
    [
        pytest.param("CPU load", "Filter: service_description = CPU load", id="exact name"),
        pytest.param("~CPU", "Filter: service_description ~ CPU", id="regular expression"),
    ],
)
def test_a_host_row_carries_the_service_its_join_column_names(
    view: View, mock_livestatus: MockLiveStatusConnection, join_value: str, expected_filter: str
) -> None:
    mock_livestatus.add_table("services", SERVICES, site="local")
    mock_livestatus.expect_query(["GET services", expected_filter, "Or: 1"], match_type="loose")
    rows: list[Row] = [{"site": "local", "host_name": "alpha"}]
    joining_view = _with_painters(
        view, [ColumnSpec(name="host"), ColumnSpec(name="service_state", join_value=join_value)]
    )

    with mock_livestatus():
        join_service_row_post_processor(joining_view, [], rows)

    assert rows[0]["JOIN"][join_value]["service_state"] == 2


def test_a_view_without_join_columns_leaves_the_rows_alone(view: View) -> None:
    rows: list[Row] = [{"site": "local", "host_name": "alpha"}]

    join_service_row_post_processor(view, [], rows)

    assert rows == [{"site": "local", "host_name": "alpha"}]
