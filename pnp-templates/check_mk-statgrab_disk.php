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

$opt[1] = "--vertical-label 'Througput (MByte/s)' -l0  -u 1 --title \"Disk throughput $hostname / $servicedesc\" ";

$def[1]  = "DEF:kb=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "CDEF:mb=kb,1024,/ " ;
$def[1] .= "AREA:mb#40c080 " ;
$def[1] .= "GPRINT:mb:LAST:\"%6.1lf MByte/s last\" " ;
$def[1] .= "GPRINT:mb:AVERAGE:\"%6.1lf MByte/s avg\" " ;
$def[1] .= "GPRINT:mb:MAX:\"%6.1lf MByte/s max\\n\" ";
?>
