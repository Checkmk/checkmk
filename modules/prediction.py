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

# Code for predictive monitoring / anomaly detection

# Export data from an RRD file. This requires an up-to-date
# version of the rrdtools.


# Fetch RRD historic metrics data of a specific service. returns a tuple
# of (step, [value1, value2, ...])
# IMPORTANT: Until we have a central library, keep this function in sync with
# the function get_rrd_data() from web/prediction.py.
def get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime):
    step = 1
    rpn = "%s.%s" % (varname, cf.lower()) # "MAX" -> "max"
    lql = "GET services\n" \
          "Columns: rrddata:m1:%s:%d:%d:%d\n" \
          "OutputFormat: python\n" \
          "Filter: host_name = %s\n" \
          "Filter: description = %s\n" % (
             rpn, fromtime, untiltime, step, hostname, service_description)
    try:
        response = eval(simple_livestatus_query(lql))[0][0]
    except Exception, e:
        if opt_debug:
            raise
        raise MKGeneralException("Cannot get historic metrics via Livestatus: %s" % e)

    if not response:
        raise MKGeneralException("Got no historic metrics")

    real_fromtime, real_untiltime, step = response[:3]
    values = response[3:]
    return step, values


daynames = [ "monday", "tuesday", "wednesday", "thursday",
             "friday", "saturday", "sunday"]

# Check wether a certain time stamp lies with in daylight safing time (DST)
def is_dst(timestamp):
    return time.localtime(timestamp).tm_isdst

# Returns the timezone *including* DST shift at a certain point of time
def timezone_at(timestamp):
    if is_dst(timestamp):
        return time.altzone
    else:
        return time.timezone

def group_by_wday(t):
    wday = time.localtime(t).tm_wday
    day_of_epoch, rel_time = divmod(t - timezone_at(t), 86400)
    return daynames[wday], rel_time

def group_by_day(t):
    return "everyday", (t - timezone_at(t)) % 86400

def group_by_day_of_month(t):
    broken = time.localtime(t)
    mday = broken[2]
    return str(mday), (t - timezone_at(t)) % 86400

def group_by_everyhour(t):
    return "everyhour", (t - timezone_at(t)) % 3600


prediction_periods = {
    "wday" : {
        "slice"     : 86400, # 7 slices
        "groupby"   : group_by_wday,
        "valid"     : 7,
    },
    "day" : {
        "slice"     : 86400, # 31 slices
        "groupby"   : group_by_day_of_month,
        "valid"     : 28,
    },
    "hour" : {
        "slice"     : 86400, # 1 slice
        "groupby"   : group_by_day,
        "valid"     : 1,
    },
    "minute" : {
        "slice"     : 3600, # 1 slice
        "groupby"   : group_by_everyhour,
        "valid"     : 24,
    },
}


def get_prediction_timegroup(t, period_info):
    # Convert to local timezone
    timegroup, rel_time = period_info["groupby"](t)
    from_time = t - rel_time
    until_time = t - rel_time + period_info["slice"]
    return timegroup, from_time, until_time, rel_time


def compute_prediction(pred_file, timegroup, params, period_info, from_time, dsname, cf):
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
        tg, fr, un, rel = get_prediction_timegroup(begin, period_info)
        if tg == timegroup:
            step, data = get_rrd_data(g_hostname, g_service_description,
                                      dsname, cf, fr, un-1)
            if smallest_step == None:
                smallest_step = step
            slices.append((fr, step / smallest_step, data))
        begin -= period_info["slice"]

    # Now we have all the RRD data we need. The next step is to consolidate
    # all that data into one new array.
    num_points = len(slices[0][2])
    consolidated = []
    for i in xrange(num_points):
        point_line = []
        for from_time, scale, data in slices:
            idx = int(i / float(scale))
            if idx < len(data):
                d = data[idx]
                if d != None:
                    point_line.append(d)
            # else:
            #     date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(fr + ((un - fr) * i / float(num_points))))
            #     print "Keine Daten fur %s / %d/%s/ %.2f " % (date_str, i, float(scale),i/float(scale))

        if point_line:
            average = sum(point_line) / len(point_line)
            consolidated.append([
                 average,
                 min(point_line),
                 max(point_line),
                 stdev(point_line, average),
            ])
        else:
            consolidated.append([None, None, None, None])

    result = {
        "num_points" : num_points,
        "step"       : smallest_step,
        "columns"    : [ "average", "min", "max", "stdev" ],
        "points"     : consolidated,
    }
    return result

def stdev(point_line, average):
    return math.sqrt(sum([ (p-average)**2 for p in point_line ]) / len(point_line))


# cf: consilidation function (MAX, MIN, AVERAGE)
# levels_factor: this multiplies all absolute levels. Usage for example
# in the cpu.loads check the multiplies the levels by the number of CPU
# cores.
def get_predictive_levels(dsname, params, cf, levels_factor=1.0):
    # Compute timegroup
    now = time.time()
    period_info = prediction_periods[params["period"]]

    # timegroup: name of the group, like 'monday' or '12'
    # from_time: absolute epoch time of the first second of the
    # current slice.
    # until_time: absolute epoch of the first second *not* in the slice
    # rel_time: seconds offset of now in the current slice
    timegroup, from_time, until_time, rel_time = \
       get_prediction_timegroup(now, period_info)

    # Compute directory for prediction data
    dir = "%s/prediction/%s/%s/%s" % (var_dir, g_hostname,
             pnp_cleanup(g_service_description), pnp_cleanup(dsname))
    if not os.path.exists(dir):
        os.makedirs(dir)

    pred_file = "%s/%s" % (dir, timegroup)
    info_file = pred_file + ".info"

    # In previous versions it could happen that the files were created with 0 bytes of size
    # which was never handled correctly so that the prediction could never be used again until
    # manual removal of the files. Clean this up.
    for file_path in [ pred_file, info_file ]:
        if os.path.exists(file_path) and os.stat(file_path).st_size == 0:
            os.unlink(file_path)

    # Check, if we need to (re-)compute the prediction file. This is
    # the case if:
    # - no prediction has been done yet for this time group
    # - the prediction from the last time is outdated
    # - the prediction from the last time has done with other parameters
    try:
        last_info = eval(file(info_file).read())
        for k, v in params.items():
            if last_info.get(k) != v:
                if opt_debug:
                    sys.stderr.write("Prediction parameters have changed.\n")
                last_info = None
                break
    except IOError:
        if opt_debug:
            sys.stderr.write("No previous prediction for group %s available.\n" % timegroup)
        last_info = None

    if last_info and last_info["time"] + period_info["valid"] * period_info["slice"] < now:
        if opt_debug:
            sys.stderr.write("Prediction of %s outdated.\n" % timegroup)
        last_info = None

    if last_info:
        # TODO: faster file format. Binary encoded?
        prediction = eval(file(pred_file).read())

    else:
        # Remove all prediction files that result from other
        # prediction periods. This is e.g. needed if the user switches
        # the parameter from 'wday' to 'day'.
        for f in os.listdir(dir):
            if f.endswith(".info"):
                try:
                    info = eval(file(dir + "/" + f).read())
                    if info["period"] != params["period"]:
                        if opt_debug:
                            sys.stderr.write("Removing obsolete prediction %s\n" % f[:-5])
                        os.remove(dir + "/" + f)
                        os.remove(dir + "/" + f[:-5])
                except:
                    pass

        if opt_debug:
            sys.stderr.write("Computing prediction for time group %s.\n" % timegroup)
        prediction = compute_prediction(pred_file, timegroup, params, period_info, from_time, dsname, cf)
        info = {
            "time"         : now,
            "range"        : (from_time, until_time),
            "cf"           : cf,
            "dsname"       : dsname,
            "slice"        : period_info["slice"],
        }
        info.update(params)
        file(info_file, "w").write("%r\n" % info)
        file(pred_file, "w").write("%r\n" % prediction)

    # Find reference value in prediction
    index = int(rel_time / prediction["step"])
    # print "rel_time: %d, step: %d, Index: %d, num_points: %d" % (rel_time, prediction["step"], index, prediction["num_points"])
    # print prediction.keys()
    reference = dict(zip(prediction["columns"], prediction["points"][index]))
    # print "Reference: %s" % reference
    ref_value = reference["average"]
    stdev = reference["stdev"]
    levels = []
    if not ref_value: # No reference data available
        levels = ((None, None), (None, None))
    else:
        for what, sig in [ ( "upper", 1 ), ( "lower", -1 )]:
            p = "levels_" + what
            if p in params:
                how, (warn, crit) = params[p]
                if how == "absolute":
                    this_levels = (ref_value + (sig * warn * levels_factor), ref_value + (sig * crit * levels_factor))
                elif how == "relative":
                    this_levels = (ref_value + sig * (ref_value * warn / 100),
                                   ref_value + sig * (ref_value * crit / 100))
                else: #  how == "stdev":
                    this_levels = (ref_value + sig * (stdev * warn),
                                  ref_value + sig * (stdev * crit))

                if what == "upper" and "levels_upper_min" in params:
                    limit_warn, limit_crit = params["levels_upper_min"]
                    this_levels = (max(limit_warn, this_levels[0]), max(limit_crit, this_levels[1]))
                levels.append(this_levels)
            else:
                levels.append((None, None))


    # print levels
    return ref_value, levels


def pnp_cleanup(s):
    return s \
        .replace(' ',  '_') \
        .replace(':',  '_') \
        .replace('/',  '_') \
        .replace('\\', '_')
