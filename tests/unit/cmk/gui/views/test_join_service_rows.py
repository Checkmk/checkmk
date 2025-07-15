#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy

import pytest

import cmk.ccc.version as cmk_version
from cmk.gui.type_defs import ColumnSpec
from cmk.gui.view import View
from cmk.gui.views._join_service_rows import _get_needed_join_columns
from cmk.utils import paths


@pytest.mark.usefixtures("load_config")
def test_get_needed_join_columns(view: View) -> None:
    view_spec = copy.deepcopy(view.spec)
    view_spec["painters"] = [
        *view_spec["painters"],
        ColumnSpec(name="service_description", join_value="CPU load"),
    ]
    view = View(view.name, view_spec, view_spec.get("context", {}))

    columns = _get_needed_join_columns(view.join_cells, view.sorters)

    expected_columns = [
        "host_name",
        "service_description",
    ]

    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CME:
        expected_columns += [
            "host_custom_variable_names",
            "host_custom_variable_values",
        ]

    assert sorted(columns) == sorted(expected_columns)
