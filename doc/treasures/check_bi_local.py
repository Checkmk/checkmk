#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

# Example for creating real Nagios checks from BI aggregations. 

# Installation:
# 1. Put this file in /usr/lib/check_mk_agent/local
# 2. Make the file executable
# 3. Add a correct url_prefix (OMD site and slash)
#    user and password with read access to Multisite. 

url_prefix = "" # non-OMD installations
# url_prefix = "mysite/" # with OMD site name

# HTTP Basic Auth
user = "omdadmin"
password = "omd"
# Alternatively: Multisite Cookie authentication:
# If you are using Cookie base authentication, then
# login with your browser and get the cookie content
# of auth_... from your browser settings and put
# it here:
# cookie = "omdadmin:1329218457.69:16b1d572fe059e00a89b7f24592733f2"


# Do not change anything below

import os, sys

if cookie:
    logininfo = ""
    opts = "-b 'auth_=%s'" % cookie
else:
    logininfo = "%s:%s@" % (user, password)
    opts = ""

url = 'http://%slocalhost/%scheck_mk/view.py?view_name=aggr_summary&output_format=python' % \
  (logininfo, url_prefix)

try:
    command = "curl --silent %s '%s'" % (opts, url)
    output = os.popen(command).read()
    data = eval(output)
except:
    sys.stderr.write("Invalid output from URL %s:\n" % url)
    sys.stderr.write(output)
    sys.stderr.write("Command was: %s\n" % command)
    sys.exit(1)

states = {
  "OK"      : 0,
  "WARN"    : 1,
  "CRIT"    : 2,
  "UNKNOWN" : 3,
}

for name, state, output in data[1:]:
    state_nr = states.get(state, -1)
    descr = "BI_Aggr_" + name.replace(" ", "_")
    if state_nr != -1:
        text = "%d %s - %s" % (state_nr, descr, state)
        if output:
            text += " - " + output
        print text

