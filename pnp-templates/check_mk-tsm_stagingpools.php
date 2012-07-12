<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

# bisect the pool name from service description, this didn't work
#$parts = explode(" ", $servicedesc);
#$pool = $parts[1];

$opt[1] = "-l0 --vertical-label \"Tapes\" --title \"Occupancy of pool\" ";



$def[1]  = "DEF:tapes=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "DEF:free=$RRDFILE[2]:$DS[1]:MAX ";
$def[1] .= "DEF:util=$RRDFILE[3]:$DS[1]:MAX ";


$def[1] .= "AREA:tapes#cd853f:\"Tapes in Pool   \" ";
$def[1] .= "AREA:free#a000ff:\"Free Tapes   \" ";
$def[1] .= "LINE:util#000000:\"Utilization   \" ";
# FIXME:
# add warn/crit lines



?>
