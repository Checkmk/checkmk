#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Code for predictive monitoring / anomaly detection

# Export data from an RRD file. This requires an up-to-date
# version of the rrdtools.

def debug(x):
    import pprint ; pprint.pprint(x)

def rrd_export(filename, ds, cf, fromtime, untiltime, rrdcached=None):
    # rrdtool xport --json -s 1361554418 -e 1361640814 --step 60 DEF:x=/omd/sites/heute/X.rrd:1:AVERAGE XPORT:x:HIRNI
    cmd = "rrdtool xport --json -s %d -e %d --step 60 " % (fromtime, untiltime)
    if rrdcached and os.path.exists(rrdcached):
        cmd += "--daemon '%s' " % rrdcached
    cmd += " DEF:x=%s:%s:%s XPORT:x 2>&1" % (filename, ds, cf)
    # if opt_debug:
    #     sys.stderr.write("Running %s\n" % cmd)
    f = os.popen(cmd)
    output = f.read()
    exit_code = f.close()
    if exit_code:
        raise MKGeneralException("Cannot fetch RRD data: %s" % output)

    # Parse without json module (this is not always available)
    # Our data begins at "data: [...". The sad thing: names are not
    # quoted here. Don't know why. We fake this by defining variables.
    about = "about"
    meta = "meta"
    start = "start"
    step = "step"
    end = "end"
    legend = "legend"
    data = "data"
    null = None

    # begin = output.index("data:")
    # data_part = output[begin + 5:-2]
    data = eval(output)

    return data["meta"]["step"], [ x[0] for x in data["data"] ]

def find_ds_in_pnp_xmlfile(xml_file, varname):
    ds = None
    name = None
    for line in file(xml_file):
        line = line.strip()
        if line.startswith("<DS>"):
            ds = line[4:].split('<')[0]
            if name == varname:
                return int(ds)
        elif line.startswith("<LABEL>"):
            name = line[7:].split('<')[0]
            if ds and name == varname:
                return int(ds)
            else:
                ds = None
        elif line == '<DATASOURCE>':
            ds = None
            name = None

def get_rrd_data(hostname, service_description, varname, cf, fromtime, untiltime):
    global rrdcached_socket
    rrd_base = "%s/%s/%s" % (rrd_path, pnp_cleanup(hostname),
             pnp_cleanup(service_description))
    # First try PNP storage type MULTIPLE
    rrd_file = rrd_base + "_%s.rrd" % pnp_cleanup(varname)
    ds = 1
    if not os.path.exists(rrd_file):
        # We need to look into the XML file of PNP in order to
        # find the correct DS number.
        xml_file = rrd_base + ".xml"
        if not os.path.exists(xml_file):
            raise MKGeneralException("Cannot do prediction: XML file %s missing" % xml_file)
        rrd_file = rrd_base + ".rrd"
        if not os.path.exists(rrd_file):
            raise MKGeneralException("Cannot do prediction: RRD file missing")

        # Let's parse the XML file in a silly, but fast way, that does
        # not need any further module.
        ds = find_ds_in_pnp_xmlfile(xml_file, varname)
        if ds == None:
            raise MKGeneralException("Cannot do prediction: variable %s not known" % varname)

    if omd_root and not rrdcached_socket:
        rrdcached_socket = omd_root + "/tmp/run/rrdcached.sock"
    return rrd_export(rrd_file, ds, cf, fromtime, untiltime, rrdcached_socket)

daynames = [ "monday", "tuesday", "wednesday", "thursday",
             "friday", "saturday", "sunday"]

def group_by_wday(t):
    wday = time.localtime(t).tm_wday
    day_of_epoch, rel_time = divmod(t - time.timezone, 86400)
    return daynames[wday], rel_time

def group_by_day(t):
    return "everyday", (t - time.timezone) % 86400

def group_by_everyhour(t):
    return "everyhour", (t - time.timezone) % 3600

prediction_periods = {
    "wday" : {
        "slice" : 86400,
        "groupby" : group_by_wday,
        "valid" : 7,
    },
    "day" : {
        "slice" : 86400,
        "groupby" : group_by_day,
        "valid" : 1,
    },
    "hour" : {
        "slice" : 3600,
        "groupby" : group_by_everyhour,
        "valid" : 1,
    }
}


def get_prediction_timegroup(t, period_info):
    # Convert to local timezone
    timegroup, rel_time = period_info["groupby"](t)
    from_time = t - rel_time
    until_time = t - rel_time + period_info["slice"]
    return timegroup, from_time, until_time, rel_time

def compute_prediction(pred_file, timegroup, params, period_info, from_time, dsname, cf):
    import math

    # Collect all slices back into the past until the time horizon
    # is reached
    begin = from_time
    slices = []
    absolute_begin = from_time - params["horizon"] * 86400
    # The resolution of the different time ranges differs. We interpolate
    # to the best resolution. We assume that the youngest slice has the
    # finest resolution. We also assume, that step step is always dividable
    # by the smallest step.
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
        # print "PUNKT %d --------------------------------------" % i
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
                    levels.append((ref_value + (sig * warn * levels_factor), ref_value + (sig * crit * levels_factor)))
                elif how == "relative":
                    levels.append((ref_value + sig * (ref_value * warn / 100),
                                   ref_value + sig * (ref_value * crit / 100)))
                else: #  how == "stdev":
                    levels.append((ref_value + sig * (stdev * warn),
                                  ref_value + sig * (stdev * crit)))
            else:
                levels.append((None, None))

    # print levels
    return ref_value, levels
