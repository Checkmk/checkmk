#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from itertools import accumulate

from ._model import Area, Stack


def bottom_above(bottom: Sequence[float], area: Area) -> Sequence[float]:
    return [base if top is None else top for base, top in zip(bottom, area.top, strict=True)]


def area_bottoms(stack: Stack, point_count: int) -> Sequence[Sequence[float]]:
    floor: Sequence[float] = [0.0] * point_count
    return list(accumulate(stack.areas, bottom_above, initial=floor))[:-1]
