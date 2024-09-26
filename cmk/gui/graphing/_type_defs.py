#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never, Literal

GraphConsolidationFunction = Literal["max", "min", "average"]
GraphPresentation = Literal["lines", "stacked", "sum", "average", "min", "max"]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]


def line_type_mirror(line_type: LineType) -> LineType:
    match line_type:
        case "line":
            return "-line"
        case "-line":
            return "line"
        case "area":
            return "-area"
        case "-area":
            return "area"
        case "stack":
            return "-stack"
        case "-stack":
            return "stack"
        case other:
            assert_never(other)
