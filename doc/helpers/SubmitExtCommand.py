#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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


statusfile  = "/home/nagios/var/status.dat"
nagios_pipe = "/home/nagios/var/rw/nagios.cmd"

# Beispielaufrufe:
#
# -x DISABLE_SVC_CHECK
# OHNE Option: Einfach nur auflisten

# Alle fs_... Dienste auf avms25 und avms26 anzeigen
# ./forall.py -d -H avms25 -H avms26 -S fs_.*

# Abschalten von allen fs_... Dienstens auf avms25 und avms26
# ./forall.py -d -H avms25 -H avms26 -S fs_.*

# Abschalten von allen IPMI auf *allen* hosts:
# ./forall.py -d -s .*IPMI.*


 
def usage():
    sys.stderr.write('''
Usage: forall.py [OPTIONS]
     
  Selection options (may be used more than once):
  
         -H  PAT     select all hosts matching regex pattern PAT
                     Leaving out -H selects all hosts
         -S  PAT     select all services matching regex pattern PATH.
                     Leaving out -S selects all services
  
   Commands (only one):

         (none)          Display selected checks         
         -d              Disable notifications on selected checks
         -e              Enable notifications on selected checks
         -x CMD          Execute Nagios command CMD on selected checks
         -c AUTHOR TEXT  Add comment
         -C              Remove comment
         
\n''');


import sys, getopt, time
try:
    opts, args = getopt.getopt(sys.argv[1:], 'edx:H:S:hc:C', ["help" ])
except getopt.GetoptError, err:
    print str(err)
    usage()
    sys.exit(1)

hostfilter = []
servicefilter = []
command = None

for o,a in opts:
    if o in [ '-h', '--help' ]:
        usage()
        sys.exit(0)

    elif o == '-H':
        hostfilter.append(a)
    elif o == '-S':
        servicefilter.append(a)
    elif o == '-d':
        command = "DISABLE_SVC_NOTIFICATIONS;%s;%s"
    elif o == '-e':
        command = "ENABLE_SVC_NOTIFICATIONS;%s;%s"
    elif o == '-C':
        command = "DEL_ALL_SVC_COMMENTS;%s;%s"
    elif o == '-c':
        if len(args) == 0:
            sys.stderr.write("Need text to add as comment!\n")
            sys.exit(1)
        command = "ADD_SVC_COMMENT;%s;%s;1;" + ("%s;%s" % (a, " ".join(args)))
    elif o == '-x':
        command = a + ";%s;%s"
                  
''' 
Status file looks like this:

servicestatus {
        host_name=zbghhs02
        service_description=Disk IO
        modified_attributes=0
        check_command=mknagios-winperf.diskstat
        check_period=24x7
        notification_period=24x7
        check_interval=1.000000
        retry_interval=1.000000
        event_handler=
        has_been_checked=1
        should_be_scheduled=0
        check_execution_time=0.000
        check_latency=5.289
        check_type=1
        current_state=0
        last_hard_state=0
        last_event_id=0
        current_event_id=0
        current_problem_id=0
        last_problem_id=0
        current_attempt=1
'''

services = []

def check_filter(item, filterlist):
    if filterlist == []:
        return True
    for p in filterlist:
        if item.find(p) >= 0:
            return True
    return False
    

for line in file(statusfile):
    line = line.strip()
    if line.startswith("servicestatus"):
        in_service = True
        service = None
        host = None
    elif line.endswith("{"):
        in_service = False
    elif line == "}" and in_service:
        if service and host:
            # check filters
            if check_filter(host, hostfilter) and \
               check_filter(service, servicefilter):
                services.append( (host, service) )
    elif line.startswith("host_name=") and in_service:
        host = line.split("=")[1]
    elif line.startswith("service_description=") and in_service:
        service = line.split("=")[1]
    

if command:
    try:
        pipe = file(nagios_pipe, "w")
    except Exception, e:
        sys.stderr.write("Cannot open Nagios command pipe: %s\n" % e)
        sys.exit(1)


timestamp = int(time.time())
for host, service in services:
    if not command:
        print "%s;%s" % (host, service)
    else:
        commandline = ("[%d] " + command + "\n") % (timestamp, host, service)
        pipe.write(commandline)
        sys.stdout.write(commandline)


      
