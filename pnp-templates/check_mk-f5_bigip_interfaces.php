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

$opt[1] = "--vertical-label \"bytes per secound\" -l0  -u 1 --title \"Traffic Utilization $hostname / $servicedesc\" ";


$def[1] =  "DEF:in=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:out=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "CDEF:kb_out=out,1024,/ " ;
$def[1] .= "CDEF:kb_in=in,1024,/ " ;
$def[1] .= "AREA:in#18DF18:\"Inbound \" " ;
$def[1] .= "GPRINT:kb_in:LAST:\"%6.2lfk last\" " ;
$def[1] .= "GPRINT:kb_in:AVERAGE:\"%6.2lfk avg\" " ;
$def[1] .= "GPRINT:kb_in:MAX:\"%6.2lfk max\\n\" ";
$def[1] .= "LINE:out#004080:\"Outbound \" " ;
$def[1] .= "GPRINT:kb_out:LAST:\"%6.2lfk last\" " ;
$def[1] .= "GPRINT:kb_out:AVERAGE:\"%6.2lfk avg\" " ;
$def[1] .= "GPRINT:kb_out:MAX:\"%6.2lfk max\\n\" " ;
?>

