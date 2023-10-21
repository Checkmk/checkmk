#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import math
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Literal, NamedTuple, Protocol

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName
from cmk.utils.log import VERBOSE
from cmk.utils.misc import pnp_cleanup
from cmk.utils.servicename import ServiceName

from ._grouping import PeriodInfo, PeriodName, time_slices, Timegroup
from ._paths import DATA_FILE_SUFFIX, INFO_FILE_SUFFIX

logger = logging.getLogger("cmk.prediction")


LevelsSpec = tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]]


class MetricRecord(Protocol):
    @property
    def window(self) -> range:
        ...

    @property
    def values(self) -> Sequence[float | None]:
        ...


class PredictionParameters(BaseModel, frozen=True):
    period: PeriodName
    horizon: int
    levels_upper: LevelsSpec | None = None
    levels_upper_min: tuple[float, float] | None = None
    levels_lower: LevelsSpec | None = None


class DataStat(NamedTuple):
    average: float
    min_: float
    max_: float
    stdev: float | None


class PredictionInfo(BaseModel, frozen=True):
    name: Timegroup
    time: int
    range: tuple[int, int]
    dsname: str
    params: PredictionParameters


class PredictionData(BaseModel, frozen=True):
    points: list[DataStat | None]
    data_twindow: list[int]
    step: int

    @property
    def num_points(self) -> int:
        return len(self.points)


class PredictionStore:
    def __init__(
        self,
        basedir: Path,
        host_name: HostName,
        service_description: ServiceName,
        dsname: str,
    ) -> None:
        self._dir = basedir / host_name / pnp_cleanup(service_description) / pnp_cleanup(dsname)

    def _data_file(self, timegroup: Timegroup) -> Path:
        return self._dir / Path(timegroup).with_suffix(DATA_FILE_SUFFIX)

    def _info_file(self, timegroup: Timegroup) -> Path:
        return self._dir / Path(timegroup).with_suffix(INFO_FILE_SUFFIX)

    def save_prediction(
        self,
        info: PredictionInfo,
        data: PredictionData,
    ) -> None:
        self._dir.mkdir(exist_ok=True, parents=True)
        self._info_file(info.name).write_text(info.json())
        self._data_file(info.name).write_text(data.json())

    def remove_prediction(self, timegroup: Timegroup) -> None:
        self._data_file(timegroup).unlink(missing_ok=True)
        self._info_file(timegroup).unlink(missing_ok=True)

    def get_info(self, timegroup: Timegroup) -> PredictionInfo | None:
        file_path = self._info_file(timegroup)
        try:
            return PredictionInfo.parse_raw(file_path.read_text())
        except FileNotFoundError:
            logger.log(VERBOSE, "No prediction info for group %s available.", timegroup)
        return None

    def get_data(self, timegroup: Timegroup) -> PredictionData | None:
        file_path = self._data_file(timegroup)
        try:
            return PredictionData.parse_raw(file_path.read_text())
        except FileNotFoundError:
            logger.log(VERBOSE, "No prediction for group %s available.", timegroup)
        return None


def compute_prediction(
    info: PredictionInfo,
    now: int,
    period_info: PeriodInfo,
    get_recorded_data: Callable[[str, int, int], MetricRecord],
) -> PredictionData:
    time_windows = time_slices(now, info.params.horizon * 86400, period_info, info.name)

    from_time = time_windows[0][0]
    raw_slices = [
        (
            response.window,
            response.values,
            from_time - start,
        )
        for start, end in time_windows
        if (response := get_recorded_data(f"{info.dsname}.max", start, end))
    ]

    return _calculate_data_for_prediction(raw_slices)


def _calculate_data_for_prediction(
    raw_slices: Sequence[tuple[range, Sequence[float | None], int]],
) -> PredictionData:
    # Upsample all time slices to same resolution
    # We assume that the youngest slice has the finest resolution.
    youngest_range = raw_slices[0][0]
    slices = [
        _forward_fill_resample(
            current_range,
            values,
            range(youngest_range.start - shift, youngest_range.stop - shift, youngest_range.step),
        )
        for current_range, values, shift in raw_slices
    ]

    return PredictionData(
        points=_data_stats(slices),
        data_twindow=[youngest_range.start, youngest_range.stop],
        step=youngest_range.step,
    )


def _forward_fill_resample(
    current_range: range, values: Sequence[float | None], new_range: range
) -> Sequence[float | None]:
    if current_range == new_range:
        return values

    idx_max = len(values) - 1
    return [
        values[max(0, min(int((t - current_range.start) / current_range.step), idx_max))]
        for t in new_range
    ]


def _data_stats(slices: Iterable[Iterable[float | None]]) -> list[DataStat | None]:
    "Statistically summarize all the upsampled RRD data"

    descriptors: list[DataStat | None] = []

    for time_column in zip(*slices):
        point_line = [x for x in time_column if x is not None]
        if point_line:
            average = sum(point_line) / float(len(point_line))
            descriptors.append(
                DataStat(
                    average=average,
                    min_=min(point_line),
                    max_=max(point_line),
                    stdev=_std_dev(point_line, average),
                )
            )
        else:
            descriptors.append(None)

    return descriptors


def _std_dev(point_line: list[float], average: float) -> float | None:
    samples = len(point_line)
    # In the case of a single data-point an unbiased standard deviation is undefined.
    if samples == 1:
        return None
    return math.sqrt(
        abs(sum(p**2 for p in point_line) - average**2 * samples) / float(samples - 1)
    )
