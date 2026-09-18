#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Callable, Sequence

type Operator = Callable[[Sequence[float | None]], float | None]


def op_sum(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def op_product(values: Sequence[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if len(present) != len(values):
        return None
    return math.prod(present)


def op_difference(values: Sequence[float | None]) -> float | None:
    minuend, subtrahend = values
    if minuend is None or subtrahend is None:
        return None
    return minuend - subtrahend


def op_fraction(values: Sequence[float | None]) -> float | None:
    dividend, divisor = values
    if dividend is None or divisor is None or divisor == 0:
        return None
    return dividend / divisor


def apply_operator(operator: Operator, values: Sequence[float | None]) -> float | None:
    if all(value is None for value in values):
        return None
    return operator(values)
