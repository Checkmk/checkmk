#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

#Author: Andreas Boesl ab@mathias-kettner.de

# This script
# 1) deletes the given hosts from WATO
# 2) creates new core config
# 3) restarts omd site
# 4) removes all data (including rrd files) from the given hosts

import os, sys, shutil, pprint

# Set automation user login credentials
automation_user   = "cmdb_automation"
automation_secret = "UVEMFMCBITYUURHPILKP"


def usage():
    print "usage: cmk_delete_host {hostname1 hostname2}"
    print "Script needs to be executed as site user"

if len(sys.argv) == 1:
    usage()
    sys.exit(1)

# Check if the given host exists
# Simple approach: Each host managed by wato has a host tag for its folder 
#                  which starts with /wato/
#                  If this is missing -> host does not exist

# Remove the host in WATO
omd_site = os.environ["OMD_SITE"]
if not omd_site:
    print "This script is only executable as site user" 
    sys.exit(1)

g_current_host = None
def log(text):
    print "%s: %s" % (g_current_host, text)

def get_wato_folder(hostname):
    process = os.popen("cmk -D " + hostname, "r")
    output  = process.read().split("\n")
    for line in output:
        if line.startswith("Tags:"):
            for tag in line.split()[1:]:
                if tag.startswith("/wato/"):
                    return tag[6:-1]
            else:
                log("Host not managed by WATO")
                break
    else:
        log("Host has no tags")
    return


# Start deletion
wato_config_changed = False
for hostname in sys.argv[1:]:
    if not hostname.strip():
        continue

    g_current_host = hostname
    wato_folder = get_wato_folder(hostname)
    if wato_folder == None:
        continue

    wato_config_changed = True
    # Remove the host in WATO
    command = "curl -s 'http://localhost/%(omd_site)s/check_mk/wato.py?mode=folder"\
    "&_username=%(automation_user)s"\
    "&_secret=%(automation_secret)s"\
    "&_do_actions=yes"\
    "&_do_confirm=yes"\
    "&_delete_host=%(hostname)s"\
    "&_transid=-1"\
    "&folder=%(wato_folder)s' 1>/dev/null" % { "automation_user": automation_user,
                                   "automation_secret": automation_secret,
                                   "omd_site": omd_site,
                                   "hostname": hostname,
                                   "wato_folder": wato_folder }

    os.system(command)

# Generate monitoring configuration and restart core
if wato_config_changed:
    os.system("cmk -R ; omd restart")

# Flushing counters, cache files, piggy files, logfiles and autochecks
print "Flushing data"
os.system("cmk --flush %s" % " ".join(sys.argv[1:]))
for hostname in sys.argv[1:]:
    if not hostname.strip():
        continue

    g_current_host = hostname

    # Remove rrd files
    path_rrd = "~/var/pnp4nagios/perfdata/" + hostname
    path_rrd = os.path.expanduser(path_rrd)
    if os.path.exists(path_rrd):
        log("Removing path " + path_rrd)
        shutil.rmtree(path_rrd)
    else:
        log("Host has no perfdata")

