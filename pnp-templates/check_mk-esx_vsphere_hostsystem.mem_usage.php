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

$opt[1] = "--vertical-label 'Memory (Bytes)' --upper-limit " . $MAX[1] . " -l0  --title \"Memory usage of $hostname\" ";

$total_gb = $MAX[1] / 1073741824.0;
$total_text = sprintf("%.2fGB", $total_gb);

$def[1] =  "DEF:used=$RRDFILE[1]:$DS[1]:MAX "
         . "CDEF:usedgb=used,1073741824,/ "
         . "HRULE:$MAX[1]#000080:\"Total memory\: $total_text\" ";
if ($WARN[1]) {
       $def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning (used)\" "
         . "HRULE:$CRIT[1]#FF0000:\"Critical (used)\" ";
}

$def[1] .= "'COMMENT:\\n' "
         . "AREA:used#20cf80:\"Used main memory   \" "
         . "GPRINT:usedgb:LAST:\"%6.2lf GB last\" " 
         . "GPRINT:usedgb:AVERAGE:\"%6.2lf GB avg\" "
         . "GPRINT:usedgb:MAX:\"%6.2lf GB max\\n\" "
         ;


$def[1] .= "LINE:used#00af60:\"\" " ;

?>
