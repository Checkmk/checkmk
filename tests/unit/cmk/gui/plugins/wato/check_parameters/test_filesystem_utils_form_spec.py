#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest

from cmk.gui.form_specs import (
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.plugins.wato.check_parameters.filesystem_utils_form_spec import fs_filesystem


@pytest.mark.parametrize(
    "disk_data, frontend_data",
    [
        pytest.param(
            {"levels": (23, 24)},
            {"levels": ("alternative_used", ("alternative_absolute", [23, 24]))},
        ),
        pytest.param(
            {"levels": (-23, -24)},
            {"levels": ("alternative_free", ("alternative_absolute", [23, 24]))},
        ),
        pytest.param(
            {"levels": (23.0, 24.0)},
            {"levels": ("alternative_used", ("alternative_percentage", [23, 24]))},
        ),
        pytest.param(
            {"levels": (-23.0, -24.0)},
            {"levels": ("alternative_free", ("alternative_percentage", [23, 24]))},
        ),
        pytest.param(
            {"levels": (-23.0, -24.0)},
            {"levels": ("alternative_free", ("alternative_percentage", [23, 24]))},
        ),
        pytest.param(
            {"levels": [(222, (-12, -32)), (4444, (-20.0, -10.0))]},
            {
                "levels": (
                    "alternative_free",
                    (
                        "alternative_dynamic",
                        [
                            [["222", "B"], ("alternative_absolute", [12, 32])],
                            [["4444", "B"], ("alternative_percentage", [20.0, 10.0])],
                        ],
                    ),
                )
            },
        ),
    ],
)
def test_filesystem_form_spec_vue_representation(
    disk_data: dict[str, Any], frontend_data: dict[str, Any]
) -> None:
    form_spec = fs_filesystem()
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=False, mask_values=False))
    computed_vue_data = visitor.to_vue(RawDiskData(disk_data))[1]
    assert computed_vue_data == frontend_data

    computed_disk_data = visitor.to_disk(RawFrontendData(frontend_data))
    assert computed_disk_data == disk_data
