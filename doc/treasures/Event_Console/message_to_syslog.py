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

# This Script enables the sending of messages to a upd syslog server
# like the integrated syslogserver of mkeventd.
#
# Bastian Kuhn, bk@mathias-kettner.de
import time
import socket
import sys

if len(sys.argv) < 6:
    print 'This script sends a message via upd to a syslogserver'
    print 'Usage: %s SYSLOGSERVER HOSTNAME PRIO APPLICATION "MESSAGE"' % sys.argv[0]
    sys.exit()

host        = sys.argv[1]
event_host  = sys.argv[2]
prio        = sys.argv[3]
application = sys.argv[4]
message     = sys.argv[5]

port = 514
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.connect((host, port))
timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
sock.send("<%s>%s %s %s: %s\n" % (prio, timestamp, event_host, application,  message))
sock.close()

