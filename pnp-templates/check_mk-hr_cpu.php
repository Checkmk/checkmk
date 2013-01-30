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

$opt[1] = "--vertical-label 'CPU utilization %' -l0  -u 100 --title \"CPU Utilization for $hostname\" ";
#
$def[1] =  "DEF:util=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "CDEF:idle=100,util,- ";

$def[1] .= "AREA:util#60f020:\"Utilization\":STACK " ;
$def[1] .= "GPRINT:util:MIN:\"Min\: %2.1lf%%\" " ;
$def[1] .= "GPRINT:util:MAX:\"Max\: %2.1lf%%\" " ;
$def[1] .= "GPRINT:util:LAST:\"Last\: %2.1lf%%\" " ;

$def[1] .= "LINE:idle#ffffff:\"Idle\" " ;
$def[1] .= "GPRINT:idle:LAST:\"%2.1lf%%\" " ;

?>
