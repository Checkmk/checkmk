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

$opt[1] = "--vertical-label 'Client Connections' -l0 --title \"$servicedesc - Connections\" ";

$def[1] = "DEF:conns=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:conns#4060a0:\"Current Client Connections\" ";
$def[1] .= "LINE:conns#203060 ";
$def[1] .= "GPRINT:conns:LAST:\"%7.0lf %s LAST\" ";
$def[1] .= "GPRINT:conns:MAX:\"%7.0lf %s MAX\\n\" ";

$opt[2] = "--vertical-label 'Connects/sec' -l0 --title \"$servicedesc - Connects\" ";

$def[2] = "DEF:conns=$RRDFILE[2]:$DS[2]:MAX ";
$def[2] .= "AREA:conns#80a0f0:\"Connects/sec\" ";
$def[2] .= "LINE:conns#4060a0 ";
$def[2] .= "GPRINT:conns:LAST:\"%7.0lf %s LAST\" ";
$def[2] .= "GPRINT:conns:MAX:\"%7.0lf %s MAX\\n\" ";
?>
