#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys

import livestatus

try:
    omd_root = os.environ["OMD_ROOT"]
except KeyError:
    sys.stderr.write("This example is indented to run in an OMD site\n")
    sys.stderr.write("Please change socket_path in this example, if you are\n")
    sys.stderr.write("not using OMD.\n")
    sys.exit(1)

socket_path = "unix:" + omd_root + "/tmp/run/live"

sites = {
    "muc": {
        "socket": socket_path,
        "alias": "Munich",
    },
    "sitea": {
        "alias": "Augsburg",
        "socket": "tcp:sitea:6557",
        "nagios_url": "/nagios/",
        "timeout": 2,
    },
    "siteb": {
        "alias": "Berlin",
        "socket": "tcp:siteb:6557",
        "nagios_url": "/nagios/",
        "tls": ("encrypted", {"verify": True}),
        "timeout": 10,
    },
}

c = livestatus.MultiSiteConnection(sites)  # type: ignore[arg-type]
c.set_prepend_site(True)
print(c.query("GET hosts\nColumns: name state\n"))
c.set_prepend_site(False)
print(c.query("GET hosts\nColumns: name state\n"))

# Beware: When doing stats, you need to aggregate yourself:
print(sum(c.query_column("GET hosts\nStats: state >= 0\n")))

# Detect errors:
sites = {
    "muc": {
        "socket": "unix:/var/run/nagios/rw/live",
        "alias": "Munich",
    },
    "sitea": {
        "alias": "Augsburg",
        "socket": "tcp:sitea:6558",  # BROKEN
        "nagios_url": "/nagios/",
        "timeout": 2,
    },
    "siteb": {
        "alias": "Berlin",
        "socket": "tcp:siteb:6557",
        "nagios_url": "/nagios/",
        "tls": ("encrypted", {"verify": True}),
        "timeout": 10,
    },
}

c = livestatus.MultiSiteConnection(sites)  # type: ignore[arg-type]
for name, state in c.query("GET hosts\nColumns: name state\n"):
    print("%-15s: %d" % (name, state))
print("Dead sites:")
for sitename, info in c.dead_sites().items():
    print("%s: %s" % (sitename, info["exception"]))
