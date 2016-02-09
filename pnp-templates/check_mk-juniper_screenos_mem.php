<?php
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

if ($MAX[1]/1024/1024 > 10000) {
    $scale = 1024 * 1024 * 1024;
    $unit = 'GB';
}
else {
    $scale = 1024 * 1024;
    $unit = 'MB';
}

$total = sprintf("%.2f", $MAX[1] / $scale);
$warn = sprintf("%.2f", $WARN[1] / $scale);
$crit = sprintf("%.2f", $CRIT[1] / $scale);

$opt[1] = "--vertical-label $unit -l 0 --title \"Main Memory (RAM)\" -X0 --upper-limit " . $total;
#

$def[1]  = "DEF:used_bytes=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "CDEF:used=used_bytes,$scale,/ ";
$def[1] .= "AREA:used#60f020:\"Used\" " ;
$def[1] .= "GPRINT:used:MIN:\"Min\: %2.1lf $unit\" " ;
$def[1] .= "GPRINT:used:MAX:\"Max\: %2.1lf $unit\" " ;
$def[1] .= "GPRINT:used:LAST:\"Last\: %2.1lf $unit\\n\" " ;
$def[1] .= "HRULE:$warn#FFFF00:\"Warn\" ";
$def[1] .= "HRULE:$crit#FF0000:\"Crit\" ";
$def[1] .= "HRULE:$total#000000:\"RAM installed $total $unit\\n\" ";
?>
