#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |                     _           _           _                    |
# |                  __| |_  ___ __| |__  _ __ | |__                 |
# |                 / _| ' \/ -_) _| / / | '  \| / /                 |
# |                 \__|_||_\___\__|_\_\_|_|_|_|_\_\                 |
# |                                   |___|                          |
# |              _   _   __  _         _        _ ____               |
# |             / | / | /  \| |__  ___| |_ __ _/ |__  |              |
# |             | |_| || () | '_ \/ -_)  _/ _` | | / /               |
# |             |_(_)_(_)__/|_.__/\___|\__\__,_|_|/_/                |
# |                                            check_mk 1.1.0beta17  |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
# 
# This file is part of check_mk 1.1.0beta17.
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

#!/usr/bin/python
# 
# Sample program for accessing the Livestatus Module
# from a python program

socket_path = "/var/lib/nagios/rw/live"

import socket
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(socket_path)

# Write command to socket
s.send("GET hosts")

# Important: Close sending direction. That way
# the other side knows, we are finished.
s.shutdown(socket.SHUT_WR)

# Now read the answer
answer = s.recv(100000000)

# Parse the answer into a table (a list of lists)
table = [ line.split(';') for line in answer.splitlines() ]

print table
