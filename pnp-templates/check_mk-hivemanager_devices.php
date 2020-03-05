<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
