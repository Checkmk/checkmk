#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Literal, Self

from pydantic import BaseModel

_LevelsSpec = tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]]

_ONE_DAY = 24 * 3600


class PredictionParameters(BaseModel, frozen=True):  # type: ignore[misc]  # hidden Any
    period: Literal["wday", "day", "hour", "minute"]
    horizon: int
    levels_upper: _LevelsSpec | None = None
    levels_upper_min: tuple[float, float] | None = None
    levels_lower: _LevelsSpec | None = None


class PredictionInfo(BaseModel, frozen=True):  # type: ignore[misc]  # hidden Any
    valid_interval: tuple[int, int]
    metric: str
    params: PredictionParameters

    @classmethod
    def make(
        cls,
        metric: str,
        params: PredictionParameters,
        now: float,
    ) -> Self:
        start_of_day = _start_of_day(now)
        return cls(
            valid_interval=(start_of_day, start_of_day + _ONE_DAY),
            metric=metric,
            params=params,
        )


def _start_of_day(timestamp: float) -> int:
    t = time.localtime(timestamp)
    sec_of_day = t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec
    return int(timestamp) - sec_of_day
