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

# This script is called by snmptrapd and sends
# all traps to the mkeventd
#
# Bastian Kuhn, bk@mathias-kettner.de
# Use this script only for testing.
# It can lead to a poor performance: for 
# every received trap the python interpreter is 
# started and the script is called

import time
import sys

site_name = "SITE"
deamon_path = "/omd/sites/%s/tmp/run/mkeventd/events" % site_name

data = []
for line in sys.stdin:
    data.append(line.strip())
msg = " ".join(data[2:])
host, ip = data[:2] 
out = open(deamon_path, "w")
timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
out.write("<5>%s %s trap: %s\n" % (timestamp, host, msg))
out.close()
