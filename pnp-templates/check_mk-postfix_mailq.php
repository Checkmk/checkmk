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

# (length=22;10;20;; size=2048;;;;)
$opt[1] = "--vertical-label Mails -l0  --title \"Mail Queue Length\" ";
$def[1] =  "DEF:length=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "HRULE:$WARN[1]#FFFF00 ";
$def[1] .= "HRULE:$CRIT[1]#FF0000 ";
$def[1] .= "AREA:length#6890a0:\"Mails\" " ;
$def[1] .= "LINE:length#2060a0 " ;
$def[1] .= "GPRINT:length:LAST:\"%6.2lf last\" " ;
$def[1] .= "GPRINT:length:AVERAGE:\"%6.2lf avg\" " ;
$def[1] .= "GPRINT:length:MAX:\"%6.2lf max\\n\" ";


$opt[2] = "--vertical-label MBytes -b1024 -X6 -l0 --title \"Mail Queue Size\" ";
$def[2] = "DEF:size=$RRDFILE[2]:$DS[2]:MAX " ;
$def[2] .= "CDEF:queue_mb=size,1048576,/ ";
$def[2] .= "AREA:queue_mb#65ab0e:\"Megabytes\" ";
$def[2] .= "LINE:queue_mb#206a0e ";
$def[2] .= "GPRINT:queue_mb:MAX:\"%6.2lf MB max\\n\" ";

# geht nicht.
#$def[2] .= "DEF:size_avg=$RRDFILE[2]:$DS[2]:AVG " ;
#$def[2] .= "DEF:size_last=$RRDFILE[2]:$DS[2]:LAST " ;
#$def[2] .= "CDEF:queue_mb_avg=size_avg,1048576,/ ";
#$def[2] .= "CDEF:queue_mb_last=size_last,1048576,/ ";
#$def[2] .= "GPRINT:queue_mb:LAST:\"%6.2lf MB last\" ";
#$def[2] .= "GPRINT:queue_mb:AVERAGE:\"%6.2lf MB avg\" ";

?>
