#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#This script is called by snmptrapd and sends
#all traps to the mkeventd
#
# Bastian Kuhn, bk@mathias-kettner.de
import time
import sys

site_name = "SITE"
deamon_path = "/omd/sites/%s/tmp/run/mkeventd/events" % site_name

data = []
for line in sys.stdin:
    data.append(line.strip())
msg = " ".join(data[2:])
host, ip = data[:2] 
out = open(deamon_path, "w")
timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
out.write("<5>%s %s trap: %s" % (timestamp, host, msg))
out.close()
~            
