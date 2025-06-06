#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel

_Direction = Literal["upper", "lower"]
_Prediction = float
_EstimatedLevels = tuple[float, float]


_ONE_DAY = 24 * 3600


class PredictionParameters(BaseModel, frozen=True):
    period: Literal["wday", "day", "hour", "minute"]
    horizon: int
    levels: tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]]
    bound: tuple[float, float] | None = None


class InjectedParameters(BaseModel, frozen=True):
    meta_file_path_template: str
    predictions: Mapping[int, tuple[_Prediction | None, _EstimatedLevels | None]]


class PredictionInfo(BaseModel, frozen=True):
    valid_interval: tuple[int, int]
    metric: str
    direction: _Direction
    params: PredictionParameters

    @classmethod
    def make(
        cls,
        metric: str,
        direction: _Direction,
        params: PredictionParameters,
        now: float,
    ) -> Self:
        start_of_day = _start_of_day(now)
        return cls(
            valid_interval=(start_of_day, start_of_day + _ONE_DAY),
            metric=metric,
            direction=direction,
            params=params,
        )


def lookup_predictive_levels(
    metric: str,
    direction: _Direction,
    parameters: PredictionParameters,
    injected: InjectedParameters,
) -> tuple[_Prediction | None, _EstimatedLevels | None]:
    meta = PredictionInfo.make(metric, direction, parameters, time.time())
    try:
        return injected.predictions[hash(meta)]
    except KeyError:
        pass

    path = Path(injected.meta_file_path_template.format(meta=meta))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(meta.model_dump_json(), encoding="utf8")
    return None, None


def _start_of_day(timestamp: float) -> int:
    t = time.localtime(timestamp)
    sec_of_day = t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec
    return int(timestamp) - sec_of_day
