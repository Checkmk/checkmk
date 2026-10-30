#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.plugins.views
from cmk.gui.views.sorter import cmp_simple_number

pytestmark = pytest.mark.usefixtures("load_plugins")


# cmk.gui.views.legacy_plugins injects it by name, so nothing but this test notices when it
# disappears or changes.
def test_cmp_custom_variable_compares_the_values_as_strings() -> None:
    cmp_custom_variable = cmk.gui.plugins.views.__dict__["cmp_custom_variable"]

    assert (
        cmp_custom_variable(
            {"custom_variables": {"EC_SL": "10"}},
            {"custom_variables": {"EC_SL": "5"}},
            "EC_SL",
            cmp_simple_number,
        )
        == -1
    )
