#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
"""Code for predictive monitoring / anomaly detection"""

import json
import math
import os
import time

import cmk.utils.debug
import cmk.utils
import cmk.utils.log
import cmk.utils.defines as defines
import cmk.utils.prediction
from cmk.utils.exceptions import MKGeneralException

logger = cmk.utils.log.get_logger(__name__)


def day_start(timestamp):
    return (timestamp - cmk.utils.prediction.timezone_at(timestamp)) % 86400


def hour_start(timestamp):
    return (timestamp - cmk.utils.prediction.timezone_at(timestamp)) % 3600


def group_by_wday(t):
    wday = time.localtime(t).tm_wday
    return defines.weekday_ids()[wday], day_start(t)


def group_by_day(t):
    return "everyday", day_start(t)


def group_by_day_of_month(t):
    mday = time.localtime(t).tm_mday
    return str(mday), day_start(t)


def group_by_everyhour(t):
    return "everyhour", hour_start(t)


prediction_periods = {
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


def get_prediction_timegroup(t, period_info):
    """
    Return:
    timegroup: name of the group, like 'monday' or '12'
    from_time: absolute epoch time of the first second of the
    current slice.
    until_time: absolute epoch time of the first second *not* in the slice
    rel_time: seconds offset of now in the current slice
    """
    # Convert to local timezone
    timegroup, rel_time = period_info["groupby"](t)
    from_time = t - rel_time
    until_time = t - rel_time + period_info["slice"]
    return timegroup, from_time, until_time, rel_time


def retrieve_grouped_data_from_rrd(hostname, service_description, timegroup, params, period_info,
                                   from_time, dsname, cf):
    # Collect all slices back into the past until the time horizon
    # is reached
    begin = from_time
    slices = []
    absolute_begin = from_time - params["horizon"] * 86400
    # The resolutions of the different time ranges differ. We interpolate
    # to the best resolution. We assume that the youngest slice has the
    # finest resolution. We also assume, that each step is always dividable
    # by the smallest step.

    # Note: due to the f**king DST, we can have several shifts between
    # DST and non-DST during are computation. We need to compensate for
    # those. DST swaps within slices are being ignored. The DST flag
    # is checked against the beginning of the slice.
    smallest_step = None
    while begin >= absolute_begin:
        tg, fr, un = get_prediction_timegroup(begin, period_info)[:3]
        if tg == timegroup:
            step, data = cmk.utils.prediction.get_rrd_data(hostname, service_description, dsname,
                                                           cf, fr, un - 1)
            if smallest_step is None:
                smallest_step = step
            slices.append((fr, step / float(smallest_step), data))
        begin -= period_info["slice"]
    return slices, smallest_step


def consolidate_data(slices):
    # Now we have all the RRD data we need. The next step is to consolidate
    # all that data into one new array.
    try:
        num_points = slices[0][2]
    except IndexError:
        raise MKGeneralException("Got no historic metrics")

    consolidated = []
    for i in xrange(len(num_points)):
        point_line = []
        for _from_time, scale, data in slices:
            if not data:
                continue
            idx = int(i / float(scale))  # left data-point mapping
            d = data[idx]
            if d is not None:
                point_line.append(d)

        if point_line:
            average = sum(point_line) / float(len(point_line))
            consolidated.append([
                average,
                min(point_line),
                max(point_line),
                stdev(point_line, average),
            ])
        else:
            consolidated.append([None, None, None, None])
    return consolidated


def aggregate_data_for_prediction_and_save(hostname, service_description, pred_file, params,
                                           period_info, dsname, cf, now):
    _clean_predictions_dir(os.path.dirname(pred_file), params)

    timegroup, from_time, until_time, _rel_time = get_prediction_timegroup(now, period_info)
    logger.verbose("Aggregating data for time group %s", timegroup)
    slices, smallest_step = retrieve_grouped_data_from_rrd(
        hostname, service_description, timegroup, params, period_info, from_time, dsname, cf)

    consolidated = consolidate_data(slices)

    data_for_pred = {
        "num_points": len(consolidated),
        "step": smallest_step,
        "columns": ["average", "min", "max", "stdev"],
        "points": consolidated,
    }

    info = {
        "time": now,
        "range": (from_time, until_time),
        "cf": cf,
        "dsname": dsname,
        "slice": period_info["slice"],
        "params": params,
    }

    with open(pred_file + '.info', "w") as fname:
        json.dump(info, fname)
    with open(pred_file, "w") as fname:
        json.dump(data_for_pred, fname)

    return data_for_pred


def stdev(point_line, average):
    samples = len(point_line)
    # In the case of a single data-point an unbiased standard deviation is
    # undefined. In this case we take the magnitude of the measured value
    # itself as a measure of the dispersion.
    if samples == 1:
        return abs(average)
    return math.sqrt(abs(sum(p**2 for p in point_line) - average**2 * samples) / float(samples - 1))


def is_prediction_up2date(pred_file, timegroup, params):
    # Check, if we need to (re-)compute the prediction file. This is
    # the case if:
    # - no prediction has been done yet for this time group
    # - the prediction from the last time is outdated
    # - the prediction from the last time was done with other parameters

    last_info = cmk.utils.prediction.retrieve_data_for_prediction(pred_file + ".info", timegroup)
    if last_info is None:
        return False

    period_info = prediction_periods[params["period"]]
    now = time.time()
    if last_info["time"] + period_info["valid"] * period_info["slice"] < now:
        logger.verbose("Prediction of %s outdated", timegroup)
        return False

    jsonized_params = json.loads(json.dumps(params))
    if last_info.get('params') != jsonized_params:
        logger.verbose("Prediction parameters have changed.")
        return False

    return True


def _clean_predictions_dir(pred_dir, params):
    # Remove all prediction files that result from other
    # prediction periods. This is e.g. needed if the user switches
    # the parameter from 'wday' to 'day'.
    for f in os.listdir(pred_dir):
        if f.endswith(".info"):
            info_file = os.path.join(pred_dir, f)
            info = cmk.utils.prediction.retrieve_data_for_prediction(info_file, '')
            if info is None or info["params"]["period"] != params["period"]:
                cmk.utils.prediction.clean_prediction_files(info_file[:-5], force=True)


# cf: consilidation function (MAX, MIN, AVERAGE)
# levels_factor: this multiplies all absolute levels. Usage for example
# in the cpu.loads check the multiplies the levels by the number of CPU
# cores.
def get_levels(hostname, service_description, dsname, params, cf, levels_factor=1.0):
    # Compute timegroup
    now = time.time()
    period_info = prediction_periods[params["period"]]

    timegroup, rel_time = period_info["groupby"](now)

    pred_dir = cmk.utils.prediction.predictions_dir(
        hostname, service_description, dsname, create=True)

    pred_file = os.path.join(pred_dir, timegroup)
    cmk.utils.prediction.clean_prediction_files(pred_file)

    if is_prediction_up2date(pred_file, timegroup, params):
        data_for_pred = cmk.utils.prediction.retrieve_data_for_prediction(pred_file, timegroup)
    else:
        data_for_pred = aggregate_data_for_prediction_and_save(
            hostname, service_description, pred_file, params, period_info, dsname, cf, now)

    # Find reference value in data_for_pred
    index = int(rel_time / data_for_pred["step"])
    reference = dict(zip(data_for_pred["columns"], data_for_pred["points"][index]))
    return cmk.utils.prediction.estimate_levels(reference, params, levels_factor)
