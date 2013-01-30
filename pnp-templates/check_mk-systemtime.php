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

$range = $CRIT[1];

$opt[1] = "--vertical-label 'offset (s)' -l -$range  -u $range --title '$hostname: system time offset to Nagios' ";

$def[1] = "DEF:offset_max=$RRDFILE[1]:$DS[1]:MAX ".
          "DEF:offset_min=$RRDFILE[1]:$DS[1]:MIN ".
          "DEF:offset_avg=$RRDFILE[1]:$DS[1]:AVERAGE ".
          "CDEF:offmax=offset_max,0,MAX ".
          "CDEF:offmin=offset_min,0,MIN ".
          "CDEF:offsetabs_min=offset_min,ABS ".
          "CDEF:offsetabs_max=offset_max,ABS ".
          "CDEF:offsetabs=offset_min,offset_max,MAX ".
          "AREA:offmax#4080ff:\"time offset \" ". 
          "AREA:offmin#4080ff ". 
          "LINE1:offmin#2060d0: ". 
          "LINE1:offmax#2060d0: ". 
          "HRULE:0#c0c0c0: ".
          "HRULE:$WARN[1]#ffff00:\"\" ".
          "HRULE:-$WARN[1]#ffff00:\"Warning\\: +/- $WARN[1] s \" ".
          "HRULE:$CRIT[1]#ff0000:\"\" ".       
          "HRULE:-$CRIT[1]#ff0000:\"Critical\\: +/- $CRIT[1] s \\n\" ".       
          "GPRINT:offset_avg:LAST:\"current\: %.1lf s\" ".
          "GPRINT:offsetabs:MAX:\"max(+/-)\: %.1lf s \" ".
          "GPRINT:offsetabs:AVERAGE:\"avg(+/-)\: %.1lf s\" ".
          "";
?>
