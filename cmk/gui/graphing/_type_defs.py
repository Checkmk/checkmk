#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

GraphConsoldiationFunction = Literal["max", "min", "average"]
GraphPresentation = Literal["lines", "stacked", "sum", "average", "min", "max"]
LineType = Literal["line", "area", "stack", "-line", "-area", "-stack"]
Operators = Literal["+", "*", "-", "/", "MAX", "MIN", "AVERAGE", "MERGE"]
