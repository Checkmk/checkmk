#!/bin/sh
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

# A helper script that build a bridge between modern livedump 
# for state export while still using legacy NSCA as transport.
# if NSCA is not a strict requirement, walk on and try livedump!

# Advantages:
# - automagic detection of NSCA-enabled devices 
# - use one bulk transfer even with NCSA
# - can run every minute

# Disadvantages:
# - still using NSCA
# - still have to maintain the config on the NSCA receiver.


# Edit these parameters and the livestatus path to match your submission config
# or source them from your submit script.
NagiosDir="/usr/local/nagios"
NscaBin="$NagiosDir/libexec/send_nsca"
NscaCfg="$NagiosDir/etc/send_nsca.cfg"
LiveStatusPipe="$NagiosDir/var/rw/livestatus.cmd"
NagiosHost="nagioshost"

# Add obsess_over_host = 1 to your filter if you wish to supress superfluous hosts.
echo "GET services
Columns: host_name description state plugin_output
Filter: obsess_over_service = 1" | unixcat $LiveStatusPipe | tr \; "\t" |  $NscaBin $NagiosHost -c $NscaCfg
