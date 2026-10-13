#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

import pytest

from cmk.gui.config import Config
from cmk.gui.type_defs import ColumnSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views._join_service_rows import _get_needed_join_columns
from cmk.web.utils.request_cache import RequestCache
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


@pytest.mark.usefixtures("load_config")
def test_get_needed_join_columns(view: View) -> None:
    view_spec = copy.deepcopy(view.spec)
    view_spec["painters"] = [
        *view_spec["painters"],
        ColumnSpec(name="service_description", join_value="CPU load"),
    ]
    view = View(
        view.name,
        view_spec,
        view_spec.get("context", {}),
        make_painter_context(UserPermissions({}, {}, {}, [])),
        RequestCache(Config()),
    )

    columns = _get_needed_join_columns(view.join_cells, view.sorters)

    expected_columns = [
        "host_name",
        "service_description",
    ]

    assert sorted(columns) == sorted(expected_columns)
