#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    sys.stdout.write("\nPerformance:\n")
    for key, value in (
        livestatus.SingleSiteConnection(socket_path).query_row_assoc("GET status").items()
    ):
        sys.stdout.write("%-30s: %s\n" % (key, value))
    sys.stdout.write("\nHosts:\n")
    hosts = livestatus.SingleSiteConnection(socket_path).query_table(
        "GET hosts\nColumns: name alias address"
    )
    for name, alias, address in hosts:
        sys.stdout.write("%-16s %-16s %s\n" % (name, address, alias))

    # Do several queries in one connection
    conn = livestatus.SingleSiteConnection(socket_path)
    num_up = conn.query_value("GET hosts\nStats: hard_state = 0")
    sys.stdout.write("\nHosts up: %d\n" % num_up)

    stats = conn.query_row(
        "GET services\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\n"
    )
    sys.stdout.write("Service stats: %d/%d/%d/%d\n" % tuple(stats))

    sys.stdout.write(
        "List of commands: %s\n" % ", ".join(conn.query_column("GET commands\nColumns: name"))
    )

    sys.stdout.write("Query error:\n")
    conn.query_value("GET hosts\nColumns: hirni")

except Exception as e:  # livestatus.MKLivestatusException, e:
    sys.stdout.write("Livestatus error: %s\n" % str(e))
