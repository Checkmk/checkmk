#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.type_defs import Perfdata
from cmk.gui.utils.html import HTML
from cmk.gui.views.perfometer.legacy_perfometers.check_mk import perfometer_fileinfo_groups
from cmk.gui.views.perfometer.legacy_perfometers.utils import LegacyPerfometerResult


@pytest.mark.parametrize(
    "perf_data, expected_result",
    [
        (
            [
                ("count", 1, "", None, None, None, None),
                ("size", 0, "", None, None, None, None),
                ("size_largest", 0, "", None, None, None, None),
                ("size_smallest", 0, "", None, None, None, None),
                ("age_oldest", 5, "", None, None, None, None),
                ("age_newest", 5, "", None, None, None, None),
            ],
            (
                "1 Tot / 5.00 s",
                HTML(
                    '<div class="stacked"><table><tr><td style="width: 10%; background-color: #aabb50" class="inner"></td>'
                    '<td style="width: 90%; background-color: #bdbdbd" class="inner"></td></tr></table>'
                    '<table><tr><td style="width: 21%; background-color: #ccff50" class="inner"></td>'
                    '<td style="width: 78%; background-color: #bdbdbd" class="inner"></td></tr></table></div>'
                ),
            ),
        ),
        (
            [("count", 0, "", None, None, None, None), ("size", 0, "", None, None, None, None)],
            (
                "0 Tot",
                HTML(
                    '<div class="stacked"><table><tr><td style="width: 0%; background-color: #aabb50" class="inner">'
                    '</td><td style="width: 100%; background-color: #bdbdbd" class="inner"></td></tr></table></div>'
                ),
            ),
        ),
    ],
)
def test_perfometer_fileinfo_groups(
    perf_data: Perfdata, expected_result: LegacyPerfometerResult
) -> None:
    assert perfometer_fileinfo_groups({}, "", perf_data) == expected_result
