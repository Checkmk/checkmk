#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

# mypy: disable-error-code="mutable-override"

import http
from dataclasses import dataclass
from typing import NewType, Self

from cmk.gui.exceptions import MKHTTPException


class MKCombinedGraphLimitExceededError(MKHTTPException):
    status = http.HTTPStatus.BAD_REQUEST


SizeEx = NewType("SizeEx", int)


# TODO: Refactor to some namespace object

KB = 1024
MB = KB * 1024
GB = MB * 1024
TB = GB * 1024
PB = TB * 1024

m = 0.001
K = 1000
M = K * 1000
G = M * 1000
T = G * 1000
P = T * 1000

scale_symbols = {
    m: "m",
    1: "",
    KB: "k",
    MB: "M",
    GB: "G",
    TB: "T",
    PB: "P",
    K: "k",
    M: "M",
    G: "G",
    T: "T",
    P: "P",
}

MAX_CORES = 128

MAX_NUMBER_HOPS = 45  # the amount of hop metrics, graphs and perfometers to create

skype_mobile_devices = [
    ("android", "Android", "33/a"),
    ("iphone", "iPhone", "42/a"),
    ("ipad", "iPad", "45/a"),
    ("mac", "Mac", "23/a"),
]


@dataclass(frozen=True, kw_only=True)
class Linear:
    slope: float
    intercept: float

    @classmethod
    def fit_to_two_points(
        cls,
        *,
        p_1: tuple[float, float],
        p_2: tuple[float, float],
    ) -> Self:
        slope = (p_2[1] - p_1[1]) / (p_2[0] - p_1[0])
        return cls(
            slope=slope,
            intercept=p_1[1] - slope * p_1[0],
        )

    def __call__(self, value: int | float) -> float:
        return self.slope * value + self.intercept
