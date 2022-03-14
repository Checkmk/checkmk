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

try:
    # Make a single connection for each query
    print("\nPerformance:")
    for key, value in (
        livestatus.SingleSiteConnection(socket_path).query_row_assoc("GET status").items()
    ):
        print("%-30s: %s" % (key, value))
    print("\nHosts:")
    hosts = livestatus.SingleSiteConnection(socket_path).query_table(
        "GET hosts\nColumns: name alias address"
    )
    for name, alias, address in hosts:
        print("%-16s %-16s %s" % (name, address, alias))

    # Do several queries in one connection
    conn = livestatus.SingleSiteConnection(socket_path)
    num_up = conn.query_value("GET hosts\nStats: hard_state = 0")
    print("\nHosts up: %d" % num_up)

    stats = conn.query_row(
        "GET services\n"
        "Stats: state = 0\n"
        "Stats: state = 1\n"
        "Stats: state = 2\n"
        "Stats: state = 3\n"
    )
    print("Service stats: %d/%d/%d/%d" % tuple(stats))

    print("List of commands: %s" % ", ".join(conn.query_column("GET commands\nColumns: name")))

    print("Query error:")
    conn.query_value("GET hosts\nColumns: hirni")

except Exception as e:  # livestatus.MKLivestatusException, e:
    print("Livestatus error: %s" % str(e))
