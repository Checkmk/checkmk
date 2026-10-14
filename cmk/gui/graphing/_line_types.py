#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import assert_never, Literal

from cmk.graphing_engine import DrawnLineType

LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]


def line_type_with_mirroring(line_type: DrawnLineType, mirrored: bool) -> LineType:
    if not mirrored:
        return line_type
    match line_type:
        case "line":
            return "-line"
        case "area":
            return "-area"
        case "stack":
            return "-stack"
        case other:
            assert_never(other)
