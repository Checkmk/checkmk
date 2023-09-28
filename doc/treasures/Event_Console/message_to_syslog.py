#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This Script enables the sending of messages to a upd syslog server
# like the integrated syslogserver of mkeventd.
#
# Bastian Kuhn, bk@mathias-kettner.de

import socket
import sys
import time

if len(sys.argv) < 6:
    print("This script sends a message via upd to a syslogserver")
    print('Usage: %s SYSLOGSERVER HOSTNAME PRIO APPLICATION "MESSAGE"' % sys.argv[0])
    sys.exit()

host = sys.argv[1]
event_host = sys.argv[2]
prio = sys.argv[3]
application = sys.argv[4]
message = sys.argv[5]

port = 514
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.connect((host, port))
timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
dgram = "<{}>{} {} {}: {}\n".format(prio, timestamp, event_host, application, message)
sock.send(dgram.encode("utf-8"))
sock.close()
