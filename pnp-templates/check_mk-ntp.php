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

$range = $CRIT[1];
$parts = explode("_", $servicedesc);
$peer = $parts[2];

$opt[1] = "--vertical-label 'offset (ms)' -l -$range  -u $range --title '$hostname: NTP time offset to $peer' ";

$def[1] = "DEF:offset=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "DEF:jitter=$RRDFILE[2]:$DS[2]:MAX ";
$def[1] .= "CDEF:offsetabs=offset,ABS ";
$def[1] .= "AREA:offset#4080ff:\"time offset \" ";
$def[1] .= "LINE1:offset#2060d0: ";
$def[1] .= "LINE2:jitter#10c000:jitter ";
$def[1] .= "HRULE:0#c0c0c0: ";
$def[1] .= "HRULE:$WARN[1]#ffff00:\"\" ";
$def[1] .= "HRULE:-$WARN[1]#ffff00:\"Warning\\: +/- $WARN[1] ms \" ";
$def[1] .= "HRULE:$CRIT[1]#ff0000:\"\" ";
$def[1] .= "HRULE:-$CRIT[1]#ff0000:\"Critical\\: +/- $CRIT[1] ms \\n\" ";
$def[1] .= "GPRINT:offset:LAST:\"current\: %.1lf ms\" ";
$def[1] .= "GPRINT:offsetabs:MAX:\"max(+/-)\: %.1lf ms \" ";
$def[1] .= "GPRINT:offsetabs:AVERAGE:\"avg(+/-)\: %.1lf ms\" ";
?>
