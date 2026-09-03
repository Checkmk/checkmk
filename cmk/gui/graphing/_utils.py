#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http
from dataclasses import dataclass
from typing import Self

from cmk.gui.exceptions import MKHTTPException


class MKCombinedGraphLimitExceededError(MKHTTPException):
    status = http.HTTPStatus.BAD_REQUEST  # type: ignore[mutable-override]


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
