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

# Old, outdated Python version of check_mkevents. Do not use
# anymore...

import os, socket, sys

try:
    socket_path = os.getenv("OMD_ROOT") + "/tmp/run/mkeventd/status"
except:
    sys.stdout.write("UNKNOWN - OMD_ROOT is not set, no socket path is defined.\n")
    sys.exit(3)

def query(query, remote_host):
    try:
        if remote_host:
            parts = remote_host.split(":")
            host = parts[0]
            if len(parts) == 2:
                port = int(parts[1])
            else:
                port = 6558
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, port))
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect(socket_path)

        sock.send(query)

        response_text = ""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return eval(response_text)
    except SyntaxError, e:
        sys.stdout.write("UNKNOWN - Invalid answer from event daemon\n%s\nQuery was:\n%s\n" \
                % (e, query))
        sys.exit(3)

    except Exception, e:
        if remote_host:
            via = "TCP %s:%d" % (host, port)
        else:
            via = "UNIX socket %s" % socket_path
        sys.stdout.write("UNKNOWN - Cannot connect to event daemon via %s: %s\n" % (via, e))
        sys.exit(3)

try:
    remote_host = None
    try:
        del sys.argv[sys.argv.index('-a')]
        opt_ignore_acknowledged = True
    except:
        opt_ignore_acknowledged = False

    try:
        del sys.argv[sys.argv.index('-l')]
        opt_less_verbose = True
    except:
        opt_less_verbose = False

    if sys.argv[1] == '-H':
        remote_host = sys.argv[2]
        del sys.argv[1:3]
    host_name = sys.argv[1]
    if len(sys.argv) > 2:
        application = sys.argv[2]
    else:
        application = None
except:
    sys.stdout.write("Usage: check_mkevents [-H (REMOTE:PORT|/path/to/unix/socket)] [-a] [-l] HOST [APPLICATION]\n")
    sys.stdout.write("\n -a        do not take into account acknowledged events.\n")
    sys.stdout.write("\n -l        less verbose output.\n")
    sys.stdout.write("\n")
    sys.exit(3)

q = "GET events\n" \
    "Filter: event_host =~ %s\n" % host_name

if application:
    q += "Filter: event_application ~~ %s\n" % application

q += "Filter: event_phase in open ack\n"

response = query(q, remote_host)
headers = response[0]
worst_state = 0
worst_row = None
count = 0
unhandled = 0
for line in response[1:]:
    count += 1
    row = dict(zip(headers, line))
    p = row["event_phase"]
    if p == 'open' or not opt_ignore_acknowledged:
        s = row["event_state"]
        if s == 3:
            if worst_state < 2:
                worst_state = 3
                worst_row = row
        elif s >= worst_state:
            worst_state = s
            worst_row = row
    if p == 'open':
        unhandled += 1

nagios_state_names = {
    0 : "OK",
    1 : "WARN",
    2 : "CRIT",
    3 : "UNKNOWN",
}

if count == 0 and application:
    sys.stdout.write("OK - no events for %s on host %s\n" % (application, host_name))
elif count == 0:
    sys.stdout.write("OK - no events for %s\n" % host_name)
else:
    if opt_less_verbose:
        sys.stdout.write(nagios_state_names[worst_state] + " - %d events" % (count))
        if worst_row:
            sys.stdout.write(" (Worst line: %s)" % (worst_row['event_text'].encode('utf-8')))
    else:
        sys.stdout.write(nagios_state_names[worst_state] + \
             " - %d events (%d unacknowledged)" % (count, unhandled))
        if worst_row:
            sys.stdout.write(", worst state is %s (Last line: %s)" % \
             (nagios_state_names[worst_state], worst_row['event_text'].encode('utf-8')))
    sys.stdout.write("\n")

sys.exit(worst_state)

