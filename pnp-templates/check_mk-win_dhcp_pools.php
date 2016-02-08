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

$opt[1] = "-l0 -u$MAX[1] --vertical-label \"IP Addresses\" --title \"$servicedesc\" ";

$def[1] = "DEF:used=$RRDFILE[2]:$DS[2]:MAX ";
$def[1] .= "DEF:pending=$RRDFILE[3]:$DS[3]:MAX ";
$def[1] .= "DEF:free=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:total=used,pending,+,free,+ ";
$def[1] .= "AREA:used#2080ff:\"Used\:         \" ";
$def[1] .= "GPRINT:used:LAST:\"%2.0lf\" ";
$def[1] .= "GPRINT:used:AVERAGE:\"(Avg\: %2.0lf,\" ";
$def[1] .= "GPRINT:used:MIN:\"Min\: %2.0lf,\" ";
$def[1] .= "GPRINT:used:MAX:\"Max\: %2.0lf)\\n\" ";
$def[1] .= "AREA:pending#8020ff:\"Pending\:      \":STACK ";
$def[1] .= "GPRINT:pending:LAST:\"%2.0lf\" ";
$def[1] .= "GPRINT:pending:AVERAGE:\"(Avg\: %2.0lf,\" ";
$def[1] .= "GPRINT:pending:MIN:\"Min\: %2.0lf,\" ";
$def[1] .= "GPRINT:pending:MAX:\"Max\: %2.0lf)\\n\" ";
$def[1] .= "AREA:free#80f0ff:\"Free\:         \":STACK ";
$def[1] .= "GPRINT:free:LAST:\"%2.0lf\" ";
$def[1] .= "GPRINT:free:AVERAGE:\"(Avg\: %2.0lf,\" ";
$def[1] .= "GPRINT:free:MIN:\"Min\: %2.0lf,\" ";
$def[1] .= "GPRINT:free:MAX:\"Max\: %2.0lf)\\n\" ";
$def[1] .= "LINE:total#666666:\"Total\:        \" ";
$def[1] .= "GPRINT:total:LAST:\"%2.0lf\\n\" ";
$def[1] .= "HRULE:$CRIT[1]#FF0000:Warning ";
$def[1] .= "HRULE:$WARN[1]#FFFF00:Critical\\n ";
?>
