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
import os
import json
import time

import six
# suppress "Cannot find module" error from mypy
import livestatus  # type: ignore
from livestatus import MKLivestatusNotFoundError

from cmk.utils.exceptions import MKGeneralException
import cmk.utils.debug
import cmk.utils.log
import cmk.utils.paths

logger = cmk.utils.log.get_logger(__name__)


# Check wether a certain time stamp lies with in daylight saving time (DST)
def is_dst(timestamp):
    return time.localtime(timestamp).tm_isdst


# Returns the timezone *including* DST shift at a certain point of time
def timezone_at(timestamp):
    if is_dst(timestamp):
        return time.altzone
    return time.timezone


def rrd_timestamps(twindow):
    start, end, step = twindow
    if step == 0:
        return []
    return [t + step for t in range(start, end, step)]


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
        if timewindow:
            self.start = timewindow[0]
            self.end = timewindow[1]
            self.step = timewindow[2]
            self.values = data
        else:
            self.start = data[0]
            self.end = data[1]
            self.step = data[2]
            self.values = data[3:]

    @property
    def twindow(self):
        return self.start, self.end, self.step

    def bfill_upsample(self, twindow, shift):
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

    def time_data_pairs(self):
        return list(zip(rrd_timestamps(self.twindow), self.values))

    def __repr__(self):
        return str(list(self.twindow) + self.values)

    def __eq__(self, other):
        if not isinstance(other, TimeSeries):
            return NotImplemented

        return self.start == other.start and self.end == other.end and self.step == other.step and self.values == other.values

    def __getitem__(self, i):
        return self.values[i]

    def __len__(self):
        return len(self.values)


def lq_logic(filter_condition, values, join):
    """JOIN with (Or, And) FILTER_CONDITION the VALUES for a livestatus query"""
    if isinstance(values, six.string_types):
        values = [values]
    conds = ["%s %s" % (filter_condition, livestatus.lqencode(x)) for x in values]
    if len(conds) > 1:
        return "\n".join(conds) + "\n%s: %d\n" % (join, len(conds))
    if conds:
        return conds[0] + '\n'
    return ""


def livestatus_lql(host_names, columns, service_descriptions=None):
    if isinstance(columns, list):
        columns = " ".join(columns)

    query_filter = "Columns: %s\n" % columns
    query_filter += lq_logic("Filter: host_name =", host_names, "Or")

    if service_descriptions == "_HOST_" or service_descriptions is None:
        what = 'host'
    else:
        what = 'service'
        query_filter += lq_logic("Filter: service_description =", service_descriptions, "Or")

    return "GET %ss\n%s" % (what, query_filter)


def get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime, max_entries=400):
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
    except MKLivestatusNotFoundError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Cannot get historic metrics via Livestatus: %s" % e)

    if response is None:
        raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

    return TimeSeries(response)


def rrd_datacolum(hostname, service_description, varname, cf):
    "Partial helper function to get rrd data"

    def time_boundaries(fromtime, untiltime):
        return get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime)

    return time_boundaries


def predictions_dir(hostname, service_description, dsname, create=False):
    pred_dir = os.path.join(cmk.utils.paths.var_dir, "prediction", hostname,
                            cmk.utils.pnp_cleanup(service_description),
                            cmk.utils.pnp_cleanup(dsname))

    if not os.path.exists(pred_dir):
        if create:
            os.makedirs(pred_dir)
        else:
            return None

    return pred_dir


def clean_prediction_files(pred_file, force=False):
    # In previous versions it could happen that the files were created with 0 bytes of size
    # which was never handled correctly so that the prediction could never be used again until
    # manual removal of the files. Clean this up.
    for file_path in [pred_file, pred_file + '.info']:
        if os.path.exists(file_path) and (os.stat(file_path).st_size == 0 or force):
            logger.verbose("Removing obsolete prediction %s", os.path.basename(file_path))
            os.remove(file_path)


def retrieve_data_for_prediction(info_file, timegroup):
    try:
        return json.loads(file(info_file).read())
    except IOError:
        logger.verbose("No previous prediction for group %s available.", timegroup)
    except ValueError:
        logger.verbose("Invalid prediction file %s, old format", info_file)
        pred_file = info_file[:-5] if info_file.endswith(".info") else info_file
        clean_prediction_files(pred_file, force=True)
    return None


def estimate_levels(reference, params, levels_factor):
    ref_value = reference["average"]
    if not ref_value:  # No reference data available
        return ref_value, [None, None, None, None]

    stdev = reference["stdev"]
    levels = []
    for what, sig in [("upper", 1), ("lower", -1)]:
        p = "levels_" + what
        if p in params:
            this_levels = estimate_level_bounds(ref_value, stdev, sig, params[p], levels_factor)

            if what == "upper" and "levels_upper_min" in params:
                limit_warn, limit_crit = params["levels_upper_min"]
                this_levels = (max(limit_warn, this_levels[0]), max(limit_crit, this_levels[1]))
            levels.extend(this_levels)
        else:
            levels.extend((None, None))
    return ref_value, levels


def estimate_level_bounds(ref_value, stdev, sig, params, levels_factor):
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
