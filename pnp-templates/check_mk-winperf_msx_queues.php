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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

$queue = str_replace("_", " ", substr($servicedesc, 6));
$opt[1] = "--vertical-label 'Queue length' -l0 --title \"$hostname / Exchange Queue: $queue\" ";

$def[1] = "DEF:length=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:length#6090ff:\"length\" ";
$def[1] .= "LINE:length#304f80 ";
$def[1] .= "GPRINT:length:LAST:\"last\: %.0lf %s\" ";
$def[1] .= "GPRINT:length:AVERAGE:\"average\: %.0lf %s\" ";
$def[1] .= "GPRINT:length:MAX:\"max\:%.0lf %s\\n\" ";
?>
