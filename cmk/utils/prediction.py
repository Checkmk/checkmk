#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
import json
import logging
import os
import time
from typing import Dict, AnyStr, Text, Union, Callable, List, Optional, Tuple, cast  # pylint: disable=unused-import

import six

import livestatus
from cmk.utils.exceptions import MKGeneralException
import cmk.utils.debug
from cmk.utils.log import VERBOSE
import cmk.utils.paths
from cmk.utils.encoding import ensure_unicode
from cmk.utils.type_defs import MetricName, ServiceName, HostName  # pylint: disable=unused-import

logger = logging.getLogger("cmk.prediction")

Seconds = int
Timestamp = int
TimeWindow = Tuple[Timestamp, Timestamp, Seconds]
RRDColumnFunction = Callable[[Timestamp, Timestamp], "TimeSeries"]
TimeSeriesValue = Optional[float]
TimeSeriesValues = List[TimeSeriesValue]
ConsolidationFunctionName = str
Timegroup = str
EstimatedLevel = Optional[float]
EstimatedLevels = Tuple[EstimatedLevel, EstimatedLevel, EstimatedLevel, EstimatedLevel]
PredictionInfo = Dict  # TODO: improve this type


def is_dst(timestamp):
    # type: (int) -> int
    """Check wether a certain time stamp lies with in daylight saving time (DST)"""
    return time.localtime(timestamp).tm_isdst


def timezone_at(timestamp):
    # type: (int) -> int
    """Returns the timezone *including* DST shift at a certain point of time"""
    if is_dst(timestamp):
        return time.altzone
    return time.timezone


def rrd_timestamps(twindow):
    # type: (TimeWindow) -> List[Timestamp]
    start, end, step = twindow
    if step == 0:
        return []
    return [t + step for t in range(start, end, step)]


def aggregation_functions(series, aggr):
    # type: (TimeSeriesValues, Optional[ConsolidationFunctionName]) -> TimeSeriesValue
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


class TimeSeries(object):
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

    """
    def __init__(self, data, timewindow=None):
        # type: (TimeSeriesValues, Optional[Tuple[float,float,float]]) -> None
        if timewindow is None:
            if data[0] is None or data[1] is None or data[2] is None:
                raise ValueError("timewindow must not contain None")

            timewindow = data[0], data[1], data[2]
            data = data[3:]

        self.start = int(timewindow[0])
        self.end = int(timewindow[1])
        self.step = int(timewindow[2])
        self.values = data

    @property
    def twindow(self):
        # type: () -> TimeWindow
        return self.start, self.end, self.step

    def bfill_upsample(self, twindow, shift):
        # type: (TimeWindow, Seconds) -> TimeSeriesValues
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

    def downsample(self, twindow, cf='max'):
        # type: (TimeWindow, ConsolidationFunctionName) -> TimeSeriesValues
        """Downsample time series by consolidation function

        twindow : 3-tuple, (start, end, step)
             description of target time interval
        cf : str ('max', 'average', 'min')
             consolidation function imitating RRD methods
        """
        dwsa = []
        i = 0
        co = []  # type: TimeSeriesValues
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

    def time_data_pairs(self):
        # type: () -> List[Tuple[Timestamp, TimeSeriesValue]]
        return list(zip(rrd_timestamps(self.twindow), self.values))

    def __repr__(self):
        # type: () -> str
        return "TimeSeries(%s, timewindow=%s)" % (self.values, self.twindow)

    def __eq__(self, other):
        # type: (object) -> bool
        if not isinstance(other, TimeSeries):
            return NotImplemented

        return self.start == other.start and self.end == other.end and self.step == other.step and self.values == other.values

    def __getitem__(self, i):
        # type: (int) -> TimeSeriesValue
        return self.values[i]

    def __len__(self):
        # type: () -> int
        return len(self.values)


def lq_logic(filter_condition, values, join):
    # type: (str, Union[AnyStr, List[AnyStr]], str) -> Text
    """JOIN with (Or, And) FILTER_CONDITION the VALUES for a livestatus query"""
    if isinstance(values, six.string_types):
        values = [values]
    conds = [u"%s %s" % (filter_condition, livestatus.lqencode(x)) for x in values]
    if len(conds) > 1:
        return ensure_unicode("\n".join(conds) + "\n%s: %d\n" % (join, len(conds)))
    if conds:
        return conds[0] + u'\n'
    return u""


# TODO: Investigate: Are there multiple service_descriptions call sites?
def livestatus_lql(host_names, columns, service_descriptions=None):
    # type: (Union[HostName, List[HostName]], Union[AnyStr, List[AnyStr]], Optional[Union[ServiceName, List[ServiceName]]]) -> Text
    if isinstance(columns, list):
        columns = " ".join(columns)

    query_filter = u"Columns: %s\n" % columns
    query_filter += lq_logic("Filter: host_name =", host_names, "Or")

    if service_descriptions == "_HOST_" or service_descriptions is None:
        what = 'host'
    else:
        what = 'service'
        query_filter += lq_logic("Filter: service_description =", service_descriptions, "Or")

    return "GET %ss\n%s" % (what, query_filter)


def get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime, max_entries=400):
    # type: (HostName, ServiceName, MetricName, ConsolidationFunctionName, Timestamp, Timestamp, int) -> TimeSeries
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

    lql = livestatus_lql(hostname, column, service_description) + "OutputFormat: python\n"

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


def rrd_datacolum(hostname, service_description, varname, cf):
    # type: (HostName, ServiceName, MetricName, ConsolidationFunctionName) -> RRDColumnFunction
    "Partial helper function to get rrd data"

    def time_boundaries(fromtime, untiltime):
        # type: (Timestamp, Timestamp) -> TimeSeries
        return get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime)

    return time_boundaries


def predictions_dir(hostname, service_description, dsname):
    # type: (HostName, ServiceName, MetricName) -> str
    return os.path.join(cmk.utils.paths.var_dir, "prediction", hostname,
                        cmk.utils.pnp_cleanup(service_description.encode("utf-8")),
                        cmk.utils.pnp_cleanup(dsname))


def clean_prediction_files(pred_file, force=False):
    # type: (Text, bool) -> None
    # In previous versions it could happen that the files were created with 0 bytes of size
    # which was never handled correctly so that the prediction could never be used again until
    # manual removal of the files. Clean this up.
    for file_path in [pred_file, pred_file + '.info']:
        if os.path.exists(file_path) and (os.stat(file_path).st_size == 0 or force):
            logger.log(VERBOSE, "Removing obsolete prediction %s", os.path.basename(file_path))
            os.remove(file_path)


def retrieve_data_for_prediction(info_file, timegroup):
    # type: (Text, Timegroup) -> Optional[PredictionInfo]
    try:
        return json.loads(open(info_file).read())
    except IOError:
        logger.log(VERBOSE, "No previous prediction for group %s available.", timegroup)
    except ValueError:
        logger.log(VERBOSE, "Invalid prediction file %s, old format", info_file)
        pred_file = info_file[:-5] if info_file.endswith(".info") else info_file
        clean_prediction_files(pred_file, force=True)
    return None


def estimate_levels(reference, params, levels_factor):
    # type: (Dict[str, int], Dict, float) -> Tuple[int, EstimatedLevels]
    ref_value = reference["average"]
    if not ref_value:  # No reference data available
        return ref_value, (None, None, None, None)

    stdev = reference["stdev"]

    def _get_levels_from_params(what, sig):
        # type: (str, int) -> Tuple[EstimatedLevel, EstimatedLevel]
        p = "levels_" + what
        if p not in params:
            return None, None

        this_levels = estimate_level_bounds(ref_value, stdev, sig, params[p], levels_factor)
        if what == "upper" and "levels_upper_min" in params:
            limit_warn, limit_crit = params["levels_upper_min"]
            this_levels = (max(limit_warn, this_levels[0]), max(limit_crit, this_levels[1]))
        return this_levels

    upper_warn, upper_crit = _get_levels_from_params("upper", 1)
    lower_warn, lower_crit = _get_levels_from_params("lower", -1)
    return ref_value, (upper_warn, upper_crit, lower_warn, lower_crit)


def estimate_level_bounds(ref_value, stdev, sig, params, levels_factor):
    # type: (int, int, int, Dict, float) -> Tuple[float, float]
    how, (warn, crit) = params
    if how == "absolute":
        return (
            ref_value + (sig * warn * levels_factor),
            ref_value + (sig * crit * levels_factor),
        )
    elif how == "relative":
        return (
            ref_value + sig * (ref_value * warn / 100.0),
            ref_value + sig * (ref_value * crit / 100.0),
        )
    # how == "stdev":
    return (
        ref_value + sig * (stdev * warn),
        ref_value + sig * (stdev * crit),
    )
