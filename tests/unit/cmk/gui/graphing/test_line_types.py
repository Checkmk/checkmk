#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing import line_type_with_mirroring


def test_a_mirrored_line_type_carries_the_minus() -> None:
    assert [
        line_type_with_mirroring(line_type, False) for line_type in ("line", "area", "stack")
    ] == [
        "line",
        "area",
        "stack",
    ]
    assert [
        line_type_with_mirroring(line_type, True) for line_type in ("line", "area", "stack")
    ] == [
        "-line",
        "-area",
        "-stack",
    ]
