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

# The number of data source various due to different
# settings (such as averaging). We rather work with names
# than with numbers.
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

$opt[1] = "--vertical-label 'Load average' -l0  -u 1 --title \"CPU Load for $hostname\" ";

$def[1] =  ""
         . "DEF:load1=$RRD[load1] "
         . "AREA:load1#60c0e0:\"Load average  1 min \" " 
         . "GPRINT:load1:LAST:\"%6.2lf last\" " 
         . "GPRINT:load1:AVERAGE:\"%6.2lf avg\" " 
         . "GPRINT:load1:MAX:\"%6.2lf max\\n\" "

         . "DEF:load15=$RRD[load15] "
         . "LINE:load15#004080:\"Load average 15 min \" " 
         . "GPRINT:load15:LAST:\"%6.2lf last\" " 
         . "GPRINT:load15:AVERAGE:\"%6.2lf avg\" " 
         . "GPRINT:load15:MAX:\"%6.2lf max\\n\" " 
         . "";

if ($WARN[1]) {
    $def[1] .= ""
         . "HRULE:$WARN[1]#FFFF00 "
         . "HRULE:$CRIT[1]#FF0000 "
         . "";
}

if (isset($RRD["predict_load15"])) {
    $def[1] .= ""
         . "DEF:predict=$RRD[predict_load15] "
         . "LINE:predict#ff0000:\"Reference for prediction \\n\" " 
         . "";
}
?>
