#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This script is called by snmptrapd and sends
# all traps to the mkeventd
#
# Bastian Kuhn, bk@mathias-kettner.de
# If you use this script please keep in mind that this script is called
# for every trap the server receives.
# To use this Script, you have to configure your snmptrad.conf like that:
# authCommunity execute public
# traphandle default /path/to/this/script

import re
import sys
import time

# Define the Hostname patterns here:
hostname_patterns = ['SMI::enterprises.2349.2.2.2.5 = "(.*)"']

# Insert here the name of your omd site
site_name = "TESTSITE"
deamon_path = "/omd/sites/%s/tmp/run/mkeventd/events" % site_name

data = []
match_host = ""
for line in sys.stdin:
    line = line.strip()
    if hostname_patterns:
        for pattern in hostname_patterns:
            e = re.search(pattern, line)
            if e:
                match_host = e.group(1)
    data.append(line)

msg = " ".join(data[2:])
host = data[0]
ip = data[1]
if match_host:
    host = match_host.strip()

# Write to mkevent Socket
out = open(deamon_path, "w")
timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
out.write("<5>{} {} trap: {}\n".format(timestamp, host, msg))
out.close()
