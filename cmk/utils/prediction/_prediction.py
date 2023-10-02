#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import math
import typing
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

import livestatus

import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.log import VERBOSE
from cmk.utils.servicename import ServiceName

from ._grouping import PeriodInfo, PeriodName, time_slices, Timegroup
from ._paths import DATA_FILE_SUFFIX, INFO_FILE_SUFFIX
from ._time_series import TimeSeries, TimeSeriesValues, Timestamp, TimeWindow

logger = logging.getLogger("cmk.prediction")

Seconds = int

RRDColumnFunction = Callable[[Timestamp, Timestamp], TimeSeries]
ConsolidationFunctionName = str
EstimatedLevel = float | None
EstimatedLevels = tuple[EstimatedLevel, EstimatedLevel, EstimatedLevel, EstimatedLevel]

LevelsSpec = tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]]


class PredictionParameters(BaseModel, frozen=True):
    period: PeriodName
    horizon: int
    levels_upper: LevelsSpec | None = None
    levels_upper_min: tuple[float, float] | None = None
    levels_lower: LevelsSpec | None = None


class DataStat(typing.NamedTuple):
    average: float
    min_: float
    max_: float
    stdev: float | None


class PredictionInfo(BaseModel, frozen=True):
    name: Timegroup
    time: int
    range: tuple[Timestamp, Timestamp]
    cf: ConsolidationFunctionName
    dsname: str
    slice: int
    params: PredictionParameters


class PredictionData(BaseModel, frozen=True):
    points: list[DataStat | None]
    data_twindow: list[Timestamp]
    step: Seconds

    @property
    def num_points(self) -> int:
        return len(self.points)


def get_rrd_data_with_mk_general_exception(
    host_name: HostName,
    service_description: str,
    metric_name: str,
    cf: ConsolidationFunctionName,
    fromtime: int,
    untiltime: int,
) -> livestatus.RRDResponse:
    """Wrapper to raise MKGeneralException."""
    try:
        response = livestatus.get_rrd_data(
            livestatus.LocalConnection(),
            host_name,
            service_description,
            f"{metric_name}.{cf.lower()}",
            fromtime,
            untiltime,
        )
    except livestatus.MKLivestatusNotFoundError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException(f"Cannot get historic metrics via Livestatus: {e}")

    if response is None:
        raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

    return response


class PredictionStore:
    def __init__(
        self,
        basedir: Path,
        host_name: HostName,
        service_description: ServiceName,
        dsname: str,
    ) -> None:
        self._dir = (
            basedir
            / host_name
            / cmk.utils.pnp_cleanup(service_description)
            / cmk.utils.pnp_cleanup(dsname)
        )

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
    prediction_store: PredictionStore,
    now: int,
    period_info: PeriodInfo,
    host_name: HostName,
    service_description: ServiceName,
) -> PredictionData:
    logger.log(VERBOSE, "Calculating prediction data for time group %s", info.name)
    prediction_store.remove_prediction(info.name)

    time_windows = time_slices(now, info.params.horizon * 86400, period_info, info.name)

    from_time = time_windows[0][0]
    rrd_responses = [
        (
            get_rrd_data_with_mk_general_exception(
                host_name,
                service_description,
                info.dsname,
                info.cf,
                start,
                end,
            ),
            from_time - start,
        )
        for start, end in time_windows
    ]

    raw_slices = [
        (
            TimeSeries(
                list(rrd_response.values),
                (rrd_response.window.start, rrd_response.window.stop, rrd_response.window.step),
            ),
            offset,
        )
        for rrd_response, offset in rrd_responses
    ]

    data_for_pred = _calculate_data_for_prediction(raw_slices)

    prediction_store.save_prediction(info, data_for_pred)

    return data_for_pred


def _calculate_data_for_prediction(
    raw_slices: Sequence[tuple[TimeSeries, int]],
) -> PredictionData:
    twindow, slices = _upsample(raw_slices)

    return PredictionData(
        points=_data_stats(slices),
        data_twindow=list(twindow[:2]),
        step=twindow[2],
    )


def _data_stats(slices: list[TimeSeriesValues]) -> list[DataStat | None]:
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


def _upsample(
    slices: Sequence[tuple[TimeSeries, int]]
) -> tuple[TimeWindow, list[TimeSeriesValues]]:
    """Upsample all time slices to same resolution

    The resolutions of the different time ranges differ. We upsample
    to the best resolution. We assume that the youngest slice has the
    finest resolution.
    """
    twindow = slices[0][0].twindow
    return twindow, [
        ts.bfill_upsample((twindow[0] - shift, twindow[1] - shift, twindow[2]))
        for ts, shift in slices
    ]
