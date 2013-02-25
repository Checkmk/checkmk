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

def rrd_export(filename, ds, fromtime, untiltime, rrdcached=None):
    # rrdtool xport --json -s 1361554418 -e 1361640814 --step 60 DEF:x=/omd/sites/heute/X.rrd:1:AVERAGE XPORT:x:HIRNI
    cmd = "rrdtool xport --json -s %d -e %d --step 60 " % (fromtime, untiltime)
    if rrdcached:
        cmd += "--daemon '%s' " % rrdcached
    cmd += " DEF:x=%s:%s:AVERAGE XPORT:x 2>&1" % (filename, ds)
    if opt_debug:
        sys.stderr.write("Running %s\n" % cmd)
    f = os.popen(cmd)
    output = f.read()
    exit_code = f.close()
    if exit_code:
        raise MKGeneralException("Cannot fetch RRD data: %s" % output)
    # Parse without json module (this is not always available)
    # Our data begins at "data: [..."
    begin = output.index("data:")
    data_part = output[begin + 5:-2]
    data = eval(data_part, { "null" : None })
    # rrdtool xport create a list for each datapoint (because you
    # can fetch several value at once)
    return [ x[0] for x in data ]

def pnp_cleanup(s):
    return s \
        .replace(' ',  '_') \
        .replace(':',  '_') \
        .replace('/',  '_') \
        .replace('\\', '_')

def get_rrd_data(hostname, service_description, varname, fromtime, untiltime):
    global rrdcached_socket
    rrd_file = "%s/%s/%s_%s.rrd" % (
            rrd_path, pnp_cleanup(hostname), pnp_cleanup(service_description), pnp_cleanup(varname))
    if omd_root and not rrdcached_socket:
        rrdcached_socket = omd_root + "/tmp/run/rrdcached.sock"
    return rrd_export(rrd_file, 1, fromtime, untiltime, rrdcached_socket)


### TEST CODE
import os, time, sys, pprint
class MKGeneralException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason
omd_root = os.getenv("OMD_ROOT") 
rrdcached_socket = None
execfile(omd_root + "/etc/check_mk/defaults")
opt_debug = True
data = get_rrd_data("test_1", "Check_MK", "execution_time", time.time() - 86400, time.time())
pprint.pprint(data)

# HINWEISE für nicht-OMD-Nutzer
# - RRD_STORAGE_TYPE muss MULTIPLE sein - single wird nicht unterstützt. Sonst
#   müssten wir noch das XML-File auswerten. 
# - rrdcached_socket muss in main.mk definiert werden, wenn rrdcached verwendet wird.
