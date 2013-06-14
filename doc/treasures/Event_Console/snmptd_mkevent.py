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
# If you use this script please keep in mind that this script is called 
# for every trap the server receives.
# To use this Script, you have to configure your snmptrad.conf like that:
# authCommunity execute public
# traphandle default /path/to/this/script

# Define the Hostname patterns here:
hostname_patterns = [
   'SMI::enterprises.2349.2.2.2.5 = "(.*)"'
]

import time
import sys
import re

site_name = os.environ.pop('OMD_SITE')
deamon_path = "/omd/sites/%s/tmp/run/mkeventd/events" % site_name

data = []
match_host = False
for line in sys.stdin:
    line = line.strip()
    if hostname_patterns:
        for pattern in hostname_patterns:
            e = re.search(pattern, line)
            if e:
                match_host = e.group(1)
    data.append(line)

msg = " ".join(data[2:])
host, ip = data[:2] 
if match_host:
    host = match_host.strip()

#Write to mkevent Socket    
out = open(deamon_path, "w")
timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
out.write("<5>%s %s trap: %s\n" % (timestamp, host, msg))
out.close()
