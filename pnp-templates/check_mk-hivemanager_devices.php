<?php
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Devices
$opt[1] = "--vertical-label 'Sessions' -l0 -X0 --title \"$servicedesc / Active Clients\" ";

$def[1] = "DEF:clients=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:clients#0030f0:\"Active Sessions\" ";
$def[1] .= "LINE:clients#001f80 ";
$def[1] .= "GPRINT:clients:LAST:\"%7.0lf %s last\" ";
$def[1] .= "GPRINT:clients:MAX:\"%7.0lf %s max\" ";
$def[1] .= "GPRINT:clients:AVERAGE:\"%7.2lf %s avg\\n\" ";
$def[1] .= "HRULE:$WARN[1]#ffff00:\"Warning at $WARN[1]\\n\" ";
$def[1] .= "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[1]\\n\" ";

# Uptime
$opt[2] = "--vertical-label 'Uptime (d)' -l0 --title \"Uptime (time since last reboot)\" ";

$def[2] = "DEF:sec=$RRDFILE[2]:$DS[2]:MAX ";
$def[2] .= "CDEF:uptime=sec,86400,/ ";
$def[2] .= "AREA:uptime#80f000:\"Uptime (days)\" ";
$def[2] .= "LINE:uptime#408000 ";
$def[2] .= "GPRINT:uptime:LAST:\"%7.2lf %s LAST\" ";
$def[2] .= "GPRINT:uptime:MAX:\"%7.2lf %s MAX\" ";
?>
