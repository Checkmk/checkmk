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

import livestatus
from livestatus import MKLivestatusNotFoundError

import cmk.debug
from cmk.exceptions import MKGeneralException
import cmk.log
import cmk.paths

logger = cmk.log.get_logger(__name__)


def lqencode(s):
    # It is not enough to strip off \n\n, because one might submit "\n \n",
    # which is also interpreted as termination of the last query and beginning
    # of the next query.
    return s.replace('\n', '')

# Check wether a certain time stamp lies with in daylight saving time (DST)
def is_dst(timestamp):
    return time.localtime(timestamp).tm_isdst


# Returns the timezone *including* DST shift at a certain point of time
def timezone_at(timestamp):
    if is_dst(timestamp):
        return time.altzone
    return time.timezone


def get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime):
    """Fetch RRD historic metrics data of a specific service, within the specified time range

    returns a tuple of (step, [value1, value2, ...])

    Query to livestatus always returns if database is found, thus:
    - Values can be None when there is no data for a given timestamp
    - If time range is smaller than data resolution the values list is empty
    - Livestatus returns a maximum of 360 data-points per query, even if
      better resolution is available within the time range.
    - There is no guarantee that query response from livestatus will
      exactly match the requested time range. Shifts on both ends will
      occur to guarantee equally spaced data-points. In the average case
      there is no problem and thus response time window is not included in
      return

    """

    step = 1
    rpn = "%s.%s" % (varname, cf.lower())  # "MAX" -> "max"

    lql = "GET services\n" \
          "Columns: rrddata:m1:%s:%s:%s:%s\n" \
          "OutputFormat: python\n" \
          "Filter: host_name = %s\n" \
          "Filter: description = %s\n" % tuple(map(lqencode,
                                                   map(str, (rpn, fromtime, untiltime, step,
                                                             hostname, service_description))))

    try:
        connection = livestatus.SingleSiteConnection("unix:%s" % cmk.paths.livestatus_unix_socket)
        response = connection.query_value(lql)
    except MKLivestatusNotFoundError as e:
        if cmk.debug.enabled():
            raise
        raise MKGeneralException("Cannot get historic metrics via Livestatus: %s" % e)

    if response is None:
        raise MKGeneralException("Cannot retrieve historic data with Nagios Core")

    step, values = response[2], response[3:]
    return step, values


def predictions_dir(hostname, service_description, dsname, create=False):
    pred_dir = os.path.join(cmk.paths.var_dir, "prediction", hostname,
                            pnp_cleanup(service_description),
                            pnp_cleanup(dsname))

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
        if os.path.exists(file_path) and os.stat(file_path).st_size == 0 or force:
            logger.verbose("Removing obsolete prediction %s", os.path.basename(file_path))
            os.remove(file_path)


def retrieve_data_for_prediction(info_file, timegroup):
    try:
        return json.loads(file(info_file).read())
    except IOError:
        logger.verbose("No previous prediction for group %s available.", timegroup)
    except ValueError:
        logger.verbose("Invalid prediction file %s, old format", info_file)
        clean_prediction_files(info_file[:-5], force=True)
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


def pnp_cleanup(s):
    return s \
        .replace(' ',  '_') \
        .replace(':',  '_') \
        .replace('/',  '_') \
        .replace('\\', '_')
