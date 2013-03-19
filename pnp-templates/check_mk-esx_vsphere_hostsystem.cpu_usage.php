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

$num_cores = $MAX[1];
$warnperc = $WARN[1] / $num_cores * 100.0;
$critperc = $CRIT[1] / $num_cores * 100.0;

$opt[1] = "--vertical-label 'Used cores' -l0  -ru $num_cores --title \"CPU Utilization for $hostname\" ";

$def[1] =  "DEF:util=$RRDFILE[1]:$DS[1]:MAX "
         . "CDEF:perc=util,$num_cores,/,100,* "
         . "AREA:util#60f020:\"Utilization\:\" "
         . "LINE:util#308010 "
         . "GPRINT:perc:LAST:\"%0.1lf%%   \" ";

if ($WARN[1]) {
    $def[1] .= "HRULE:$WARN[1]#fff000:\"Warn at $warnperc%    \" "
            . "HRULE:$CRIT[1]#ff0000:\"Critical at $critperc%\\n\" ";
}
else {
    $def[1] .= "COMMENT:\"\\n\" ";
}

$def[1] .= "HRULE:$MAX[1]#0040d0:\"$num_cores Cores installed   \" "
         . "GPRINT:util:MIN:\"Min\: %5.2lf Cores \" "
         . "GPRINT:util:MAX:\"Max\: %5.2lf Cores\" "
         . "GPRINT:util:LAST:\"Last\: %4.1lf Cores\\n\" "
         ;

?>
