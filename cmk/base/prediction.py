#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for predictive monitoring / anomaly detection"""

import json
import logging
import math
import os
import time
from typing import Optional, List, Any, cast, Dict, Union, Callable, Tuple, TypedDict

import cmk.utils.debug
import cmk.utils
import cmk.utils.defines as defines
import cmk.utils.store as store
from cmk.utils.log import VERBOSE
import cmk.utils.prediction
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import HostName, ServiceName, MetricName
from cmk.utils.prediction import (
    Timestamp,
    Timegroup,
    TimeSeriesValues,
    Seconds,
    TimeWindow,
    RRDColumnFunction,
    PredictionInfo,
    ConsolidationFunctionName,
    EstimatedLevels,
)

logger = logging.getLogger("cmk.prediction")

GroupByFunction = Callable[[Timestamp], Tuple[Timegroup, Timestamp]]
PeriodInfo = Dict[str, Union[GroupByFunction, int]]
TimeSlices = List[Tuple[Timestamp, Timestamp]]
DataStatValue = Optional[float]
DataStat = List[DataStatValue]
DataStats = List[DataStat]
PredictionParameters = Dict[str, Any]

# TODO: This is somehow related to cmk.utils.prediction.PreditionInfo,
# but using this *instead* of PredicionInfo (==Dict) is not possible.
PredictionData = TypedDict(
    'PredictionData',
    {
        "columns": List[str],
        "points": DataStats,
        "num_points": int,
        "data_twindow": List[Timestamp],
        "step": Seconds,
    },
    total=False,
)


def window_start(timestamp: int, span: int) -> int:
    """If time is partitioned in SPAN intervals, how many seconds is TIMESTAMP away from the start

    It works well across time zones, but has an unfair behavior with daylight savings time."""
    return (timestamp - cmk.utils.prediction.timezone_at(timestamp)) % span


def group_by_wday(t: Timestamp) -> Tuple[Timegroup, Timestamp]:
    wday = time.localtime(t).tm_wday
    return defines.weekday_ids()[wday], window_start(t, 86400)


def group_by_day(t: Timestamp) -> Tuple[Timegroup, Timestamp]:
    return "everyday", window_start(t, 86400)


def group_by_day_of_month(t: Timestamp) -> Tuple[Timegroup, Timestamp]:
    mday = time.localtime(t).tm_mday
    return str(mday), window_start(t, 86400)


def group_by_everyhour(t: Timestamp) -> Tuple[Timegroup, Timestamp]:
    return "everyhour", window_start(t, 3600)


prediction_periods: Dict[str, PeriodInfo] = {
    "wday": {
        "slice": 86400,  # 7 slices
        "groupby": group_by_wday,
        "valid": 7,
    },
    "day": {
        "slice": 86400,  # 31 slices
        "groupby": group_by_day_of_month,
        "valid": 28,
    },
    "hour": {
        "slice": 86400,  # 1 slice
        "groupby": group_by_day,
        "valid": 1,
    },
    "minute": {
        "slice": 3600,  # 1 slice
        "groupby": group_by_everyhour,
        "valid": 24,
    },
}


def get_prediction_timegroup(
        t: Timestamp, period_info: PeriodInfo) -> Tuple[Timegroup, Timestamp, Timestamp, Seconds]:
    """
    Return:
    timegroup: name of the group, like 'monday' or '12'
    from_time: absolute epoch time of the first second of the
    current slice.
    until_time: absolute epoch time of the first second *not* in the slice
    rel_time: seconds offset of now in the current slice
    """
    # Convert to local timezone
    group_by_function = period_info["groupby"]
    if not callable(group_by_function):
        raise RuntimeError()

    timegroup, rel_time = group_by_function(t)
    from_time = t - rel_time
    until_time = from_time + cast(int, period_info["slice"])
    return timegroup, from_time, until_time, rel_time


def time_slices(timestamp: Timestamp, horizon: Seconds, period_info: PeriodInfo,
                timegroup: Timegroup) -> TimeSlices:
    "Collect all slices back into the past until time horizon is reached"
    timestamp = int(timestamp)
    abs_begin = timestamp - horizon
    slices = []

    # Note: due to the f**king DST, we can have several shifts between DST
    # and non-DST during a computation. Treatment is unfair on those longer
    # or shorter days. All days have 24hrs. DST swaps within slices are
    # being ignored, we work with slice shifts. The DST flag is checked
    # against the query timestamp. In general that means test is done at
    # the beginning of the day(because predictive levels refresh at
    # midnight) and most likely before DST swap is applied.

    # Have fun understanding the tests for this function.

    sl = cast(int, period_info["slice"])
    for begin in range(timestamp, abs_begin, -sl):
        tg, start, end = get_prediction_timegroup(begin, period_info)[:3]
        if tg == timegroup:
            slices.append((start, end))
    return slices


def retrieve_grouped_data_from_rrd(
        rrd_column: RRDColumnFunction,
        time_windows: TimeSlices) -> Tuple[TimeWindow, List[TimeSeriesValues]]:
    "Collect all time slices and up-sample them to same resolution"
    from_time = time_windows[0][0]

    slices = [(rrd_column(start, end), from_time - start) for start, end in time_windows]

    # The resolutions of the different time ranges differ. We upsample
    # to the best resolution. We assume that the youngest slice has the
    # finest resolution.
    twindow = slices[0][0].twindow
    if twindow[2] == 0:
        raise MKGeneralException("Got no historic metrics")

    return twindow, [ts.bfill_upsample(twindow, shift) for ts, shift in slices]


def data_stats(slices: List[TimeSeriesValues]) -> DataStats:
    "Statistically summarize all the upsampled RRD data"

    descriptors: DataStats = []

    for time_column in zip(*slices):
        point_line = [x for x in time_column if x is not None]
        if point_line:
            average = sum(point_line) / float(len(point_line))
            descriptors.append([
                average,
                min(point_line),
                max(point_line),
                stdev(point_line, average),
            ])
        else:
            descriptors.append([None, None, None, None])

    return descriptors


def calculate_data_for_prediction(time_windows: TimeSlices,
                                  rrd_datacolumn: RRDColumnFunction) -> PredictionData:
    twindow, slices = retrieve_grouped_data_from_rrd(rrd_datacolumn, time_windows)

    descriptors = data_stats(slices)

    return {
        u"columns": [u"average", u"min", u"max", u"stdev"],
        u"points": descriptors,
        u"num_points": len(descriptors),
        u"data_twindow": list(twindow[:2]),
        u"step": twindow[2],
    }


def save_predictions(pred_file: str, info: PredictionInfo, data_for_pred: PredictionData) -> None:
    with open(pred_file + '.info', "w") as fname:
        json.dump(info, fname)
    with open(pred_file, "w") as fname:
        json.dump(data_for_pred, fname)


def stdev(point_line: List[float], average: float) -> float:
    samples = len(point_line)
    # In the case of a single data-point an unbiased standard deviation is
    # undefined. In this case we take the magnitude of the measured value
    # itself as a measure of the dispersion.
    if samples == 1:
        return abs(average)
    return math.sqrt(abs(sum(p**2 for p in point_line) - average**2 * samples) / float(samples - 1))


def is_prediction_up2date(pred_file: str, timegroup: Timegroup,
                          params: PredictionParameters) -> bool:
    """Check, if we need to (re-)compute the prediction file.

    This is the case if:
    - no prediction has been done yet for this time group
    - the prediction from the last time is outdated
    - the prediction from the last time was done with other parameters
    """
    last_info = cmk.utils.prediction.retrieve_data_for_prediction(pred_file + ".info", timegroup)
    if last_info is None:
        return False

    period_info = prediction_periods[params["period"]]
    now = time.time()
    if last_info["time"] + cast(int, period_info["valid"]) * cast(int, period_info["slice"]) < now:
        logger.log(VERBOSE, "Prediction of %s outdated", timegroup)
        return False

    jsonized_params = json.loads(json.dumps(params))
    if last_info.get('params') != jsonized_params:
        logger.log(VERBOSE, "Prediction parameters have changed.")
        return False

    return True


# cf: consilidation function (MAX, MIN, AVERAGE)
# levels_factor: this multiplies all absolute levels. Usage for example
# in the cpu.loads check the multiplies the levels by the number of CPU
# cores.
def get_levels(
    hostname: HostName,
    service_description: ServiceName,
    dsname: MetricName,
    params: PredictionParameters,
    cf: ConsolidationFunctionName,
    levels_factor: float = 1.0,
) -> Tuple[Optional[float], EstimatedLevels]:
    now = int(time.time())
    period_info: Dict = prediction_periods[params["period"]]

    timegroup, rel_time = cast(GroupByFunction, period_info["groupby"])(now)

    pred_dir = cmk.utils.prediction.predictions_dir(hostname, service_description, dsname)
    store.makedirs(pred_dir)

    pred_file = os.path.join(pred_dir, timegroup)
    cmk.utils.prediction.clean_prediction_files(pred_file)

    data_for_pred: Optional[PredictionData] = None
    if is_prediction_up2date(pred_file, timegroup, params):
        # Suppression: I am not sure how to check what this function returns
        #              For now I hope this is compatible.
        data_for_pred = cmk.utils.prediction.retrieve_data_for_prediction(  # type: ignore[assignment]
            pred_file, timegroup)

    if data_for_pred is None:
        logger.log(VERBOSE, "Calculating prediction data for time group %s", timegroup)
        cmk.utils.prediction.clean_prediction_files(pred_file, force=True)

        time_windows = time_slices(now, int(params["horizon"] * 86400), period_info, timegroup)

        rrd_datacolumn = cmk.utils.prediction.rrd_datacolum(hostname, service_description, dsname,
                                                            cf)

        data_for_pred = calculate_data_for_prediction(time_windows, rrd_datacolumn)

        info: PredictionInfo = {
            u"time": now,
            u"range": time_windows[0],
            u"cf": cf,
            u"dsname": dsname,
            u"slice": period_info["slice"],
            u"params": params,
        }
        save_predictions(pred_file, info, data_for_pred)

    # Find reference value in data_for_pred
    index = int(rel_time / cast(int, data_for_pred["step"]))  # fixed: true-division
    reference = dict(zip(data_for_pred["columns"], data_for_pred["points"][index]))
    return cmk.utils.prediction.estimate_levels(reference, params, levels_factor)
