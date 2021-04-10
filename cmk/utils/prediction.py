#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
import time
from typing import Dict, Callable, List, Optional, Tuple, Iterator

from six import ensure_str

import livestatus
from cmk.utils.exceptions import MKGeneralException
import cmk.utils.debug
from cmk.utils.log import VERBOSE
import cmk.utils.paths
from cmk.utils.type_defs import Timestamp, Seconds, MetricName, ServiceName, HostName

logger = logging.getLogger("cmk.prediction")

TimeWindow = Tuple[Timestamp, Timestamp, Seconds]
RRDColumnFunction = Callable[[Timestamp, Timestamp], "TimeSeries"]
TimeSeriesValue = Optional[float]
TimeSeriesValues = List[TimeSeriesValue]
ConsolidationFunctionName = str
Timegroup = str
EstimatedLevel = Optional[float]
EstimatedLevels = Tuple[EstimatedLevel, EstimatedLevel, EstimatedLevel, EstimatedLevel]
PredictionInfo = Dict  # TODO: improve this type


def is_dst(timestamp: float) -> bool:
    """Check wether a certain time stamp lies with in daylight saving time (DST)"""
    return bool(time.localtime(timestamp).tm_isdst)


def timezone_at(timestamp: float) -> int:
    """Returns the timezone *including* DST shift at a certain point of time"""
    return time.altzone if is_dst(timestamp) else time.timezone


def rrd_timestamps(twindow: TimeWindow) -> List[Timestamp]:
    start, end, step = twindow
    if step == 0:
        return []
    return [t + step for t in range(start, end, step)]


def aggregation_functions(series: TimeSeriesValues,
                          aggr: Optional[ConsolidationFunctionName]) -> TimeSeriesValue:
    """Aggregate data in series list according to aggr

    If series has None values they are dropped before aggregation"""
    if aggr is None:
        aggr = "max"
    aggr = aggr.lower()

    if not series or all(x is None for x in series):
        return None

    cleaned_series = [x for x in series if x is not None]

    if aggr == 'average':
        return sum(cleaned_series) / float(len(cleaned_series))
    if aggr == 'max':
        return max(cleaned_series)
    if aggr == 'min':
        return min(cleaned_series)

    raise ValueError("Invalid Aggregation function %s, only max, min, average allowed" % aggr)


class TimeSeries:
    """Describes the returned time series returned by livestatus

    - Timestamped values are valid for the measurement interval:
        [timestamp-step; timestamp[
      which means they are at the end of the interval.
    - The Series describes the interval [start; end[
    - Start has no associated value to it.

    args:
        data : List
            Includes [start, end, step, *values]
        timewindow: tuple
            describes (start, end, step), in this case data has only values
        **metadata:
            additional information arguments

    """
    def __init__(self,
                 data: TimeSeriesValues,
                 timewindow: Optional[Tuple[float, float, float]] = None,
                 **metadata: str) -> None:
        if timewindow is None:
            if data[0] is None or data[1] is None or data[2] is None:
                raise ValueError("timewindow must not contain None")

            timewindow = data[0], data[1], data[2]
            data = data[3:]

        self.start = int(timewindow[0])
        self.end = int(timewindow[1])
        self.step = int(timewindow[2])
        self.values = data
        self.metadata = metadata

    @property
    def twindow(self) -> TimeWindow:
        return self.start, self.end, self.step

    def bfill_upsample(self, twindow: TimeWindow, shift: Seconds) -> TimeSeriesValues:
        """Upsample by backward filling values

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        """
        upsa = []
        i = 0
        start, end, step = twindow
        current_times = rrd_timestamps(self.twindow)
        if start != self.start or end != self.end or step != self.step:
            for t in range(start, end, step):
                if t >= current_times[i] + shift:
                    i += 1
                upsa.append(self.values[i])

            return upsa

        return self.values

    def downsample(self,
                   twindow: TimeWindow,
                   cf: ConsolidationFunctionName = 'max') -> TimeSeriesValues:
        """Downsample time series by consolidation function

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        cf : str ('max', 'average', 'min')
             consolidation function imitating RRD methods
        """
        dwsa = []
        i = 0
        co: TimeSeriesValues = []
        start, end, step = twindow
        desired_times = rrd_timestamps(twindow)
        if start != self.start or end != self.end or step != self.step:
            for t, val in self.time_data_pairs():
                if t > desired_times[i]:
                    dwsa.append(aggregation_functions(co, cf))
                    co = []
                    i += 1
                co.append(val)

            diff_len = len(desired_times) - len(dwsa)
            if diff_len > 0:
                dwsa.append(aggregation_functions(co, cf))
                dwsa = dwsa + [None] * (diff_len - 1)

            return dwsa
        return self.values

    def time_data_pairs(self) -> List[Tuple[Timestamp, TimeSeriesValue]]:
        return list(zip(rrd_timestamps(self.twindow), self.values))

    def __repr__(self) -> str:
        return "TimeSeries(%s, timewindow=%s)" % (self.values, self.twindow)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeSeries):
            return NotImplemented

        return self.start == other.start and self.end == other.end and self.step == other.step and self.values == other.values

    def __getitem__(self, i: int) -> TimeSeriesValue:
        return self.values[i]

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self) -> Iterator[TimeSeriesValue]:
        yield from self.values


def lq_logic(filter_condition: str, values: List[str], join: str) -> str:
    """JOIN with (Or, And) FILTER_CONDITION the VALUES for a livestatus query"""
    conditions = u"".join(u"%s %s\n" % (filter_condition, livestatus.lqencode(x)) for x in values)
    connective = u"%s: %d\n" % (join, len(values)) if len(values) > 1 else u""
    return conditions + connective


def livestatus_lql(host_names: List[HostName],
                   columns: List[str],
                   service_description: Optional[ServiceName] = None) -> str:
    query_filter = u"Columns: %s\n" % u" ".join(columns)
    query_filter += lq_logic(u"Filter: host_name =", [ensure_str(n) for n in host_names], u"Or")
    if service_description == "_HOST_" or service_description is None:
        what = 'host'
    else:
        what = 'service'
        query_filter += lq_logic(u"Filter: service_description =",
                                 [ensure_str(service_description)], u"Or")
    return "GET %ss\n%s" % (what, query_filter)


def get_rrd_data(hostname: HostName,
                 service_description: ServiceName,
                 varname: MetricName,
                 cf: ConsolidationFunctionName,
                 fromtime: Timestamp,
                 untiltime: Timestamp,
                 max_entries: int = 400) -> TimeSeries:
    """Fetch RRD historic metrics data of a specific service, within the specified time range

    returns a TimeSeries object holding interval and data information

    Query to livestatus always returns if database is found, thus:
    - Values can be None when there is no data for a given timestamp
    - Reply from livestatus/rrdtool is always enough to describe the
      queried interval. That means, the returned bounds are always outside
      the queried interval.

    LEGEND
    O timestamps of measurements
    | query values, fromtime and untiltime
    x returned start, no data contained
    v returned data rows, includes end y

    --O---O---O---O---O---O---O---O
            |---------------|
          x---v---v---v---v---y

    """

    step = 1
    rpn = "%s.%s" % (varname, cf.lower())  # "MAX" -> "max"
    point_range = ":".join(
        livestatus.lqencode(str(x)) for x in (fromtime, untiltime, step, max_entries))
    column = "rrddata:m1:%s:%s" % (rpn, point_range)

    lql = livestatus_lql([hostname], [column], service_description) + "OutputFormat: python\n"

    try:
        connection = livestatus.SingleSiteConnection("unix:%s" %
                                                     cmk.utils.paths.livestatus_unix_socket)
        response = connection.query_value(lql)
    except livestatus.MKLivestatusNotFoundError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Cannot get historic metrics via Livestatus: %s" % e)

    if response is None:
        raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

    return TimeSeries(response)


def rrd_datacolum(hostname: HostName, service_description: ServiceName, varname: MetricName,
                  cf: ConsolidationFunctionName) -> RRDColumnFunction:
    "Partial helper function to get rrd data"

    def time_boundaries(fromtime: Timestamp, untiltime: Timestamp) -> TimeSeries:
        return get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime)

    return time_boundaries


def predictions_dir(hostname: HostName, service_description: ServiceName,
                    dsname: MetricName) -> str:
    return os.path.join(cmk.utils.paths.var_dir, "prediction", hostname,
                        cmk.utils.pnp_cleanup(ensure_str(service_description)),
                        cmk.utils.pnp_cleanup(dsname))


def clean_prediction_files(pred_file: str, force: bool = False) -> None:
    # In previous versions it could happen that the files were created with 0 bytes of size
    # which was never handled correctly so that the prediction could never be used again until
    # manual removal of the files. Clean this up.
    for file_path in [pred_file, pred_file + '.info']:
        if os.path.exists(file_path) and (os.stat(file_path).st_size == 0 or force):
            logger.log(VERBOSE, "Removing obsolete prediction %s", os.path.basename(file_path))
            os.remove(file_path)


# TODO: We should really *parse* the loaded data, currently the type signature
# is a blatant lie!
# (mo) And, in fact, this function returns at least 2 different types of dataset.
def retrieve_data_for_prediction(info_file: str, timegroup: Timegroup) -> Optional[PredictionInfo]:
    try:
        return json.loads(open(info_file).read())
    except IOError:
        logger.log(VERBOSE, "No previous prediction for group %s available.", timegroup)
    except ValueError:
        logger.log(VERBOSE, "Invalid prediction file %s, old format", info_file)
        pred_file = info_file[:-5] if info_file.endswith(".info") else info_file
        clean_prediction_files(pred_file, force=True)
    return None


def estimate_levels(
    reference: Dict[str, Optional[float]],
    params: Dict,
    levels_factor: float,
) -> Tuple[Optional[float], EstimatedLevels]:
    ref_value = reference["average"]
    if not ref_value:  # No reference data available
        return ref_value, (None, None, None, None)

    stdev = reference["stdev"]

    levels_upper = _get_levels_from_params("upper", 1, params, ref_value, stdev, levels_factor)
    levels_lower = _get_levels_from_params("lower", -1, params, ref_value, stdev, levels_factor)
    return ref_value, levels_upper + levels_lower


def _get_levels_from_params(
    what: str,
    sig: int,
    params: Dict,
    ref_value: float,
    stdev: Optional[float],
    levels_factor: float,
) -> Tuple[EstimatedLevel, EstimatedLevel]:
    p = "levels_" + what
    if p not in params:
        return None, None

    this_levels = estimate_level_bounds(ref_value, stdev, sig, params[p], levels_factor)
    if what == "upper" and "levels_upper_min" in params:
        limit_warn, limit_crit = params["levels_upper_min"]
        this_levels = (max(limit_warn, this_levels[0]), max(limit_crit, this_levels[1]))
    return this_levels


def estimate_level_bounds(
    ref_value: float,
    stdev: Optional[float],
    sig: int,
    params: Tuple[str, Tuple[float, float]],
    levels_factor: float,
) -> Tuple[float, float]:
    how, (warn, crit) = params
    if how == "absolute":
        return (
            ref_value + (sig * warn * levels_factor),
            ref_value + (sig * crit * levels_factor),
        )
    if how == "relative":
        return (
            ref_value + sig * (ref_value * warn / 100.0),
            ref_value + sig * (ref_value * crit / 100.0),
        )

    # how == "stdev":
    if stdev is None:  # just make explicit what would have happend anyway:
        raise TypeError("stdev is None")

    return (
        ref_value + sig * (stdev * warn),
        ref_value + sig * (stdev * crit),
    )
