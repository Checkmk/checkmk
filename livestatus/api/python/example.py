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
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

import os, sys
import livestatus

try:
    omd_root = os.getenv("OMD_ROOT")
    socket_path = "unix:" + omd_root + "/tmp/run/live"
except:
    sys.stderr.write("This example is indented to run in an OMD site\n")
    sys.stderr.write("Please change socket_path in this example, if you are\n")
    sys.stderr.write("not using OMD.\n")
    sys.exit(1)

try:
   # Make a single connection for each query
   print "\nPerformance:"
   for key, value in livestatus.SingleSiteConnection(socket_path).query_row_assoc("GET status").items():
      print "%-30s: %s" % (key, value)
   print "\nHosts:"
   hosts = livestatus.SingleSiteConnection(socket_path).query_table("GET hosts\nColumns: name alias address")
   for name, alias, address in hosts:
      print "%-16s %-16s %s" % (name, address, alias)

   # Do several queries in one connection
   conn = livestatus.SingleSiteConnection(socket_path)
   num_up = conn.query_value("GET hosts\nStats: hard_state = 0")
   print "\nHosts up: %d" % num_up

   stats = conn.query_row(
	 "GET services\n"
	 "Stats: state = 0\n"
	 "Stats: state = 1\n"
	 "Stats: state = 2\n"
	 "Stats: state = 3\n")
   print "Service stats: %d/%d/%d/%d" % tuple(stats)

   print "List of commands: %s" % \
      ", ".join(conn.query_column("GET commands\nColumns: name"))

   print "Query error:"
   conn.query_value("GET hosts\nColumns: hirni")


except Exception, e: # livestatus.MKLivestatusException, e:
   print "Livestatus error: %s" % str(e)


