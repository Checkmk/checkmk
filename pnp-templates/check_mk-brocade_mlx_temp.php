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

$opt[1] = "--vertical-label $UNIT[1] --slope-mode -l0 -u 45 --title \"" . $this->MACRO['DISP_HOSTNAME'] . ' / ' . $this->MACRO['DISP_SERVICEDESC'] . "\" -w 600";

$line_colors = array( "5f7a2f", "2f8077", "2f5580", "662f80", "802f71", "802f36", "804b2f", "80762f");
$def[1] = "";

foreach ($NAME as $i => $n) {
    $def[1] .= "DEF:$n=$RRDFILE[$i]:$DS[1]:AVERAGE ";
}
foreach ($NAME as $i => $n) {
    $ii = $i % 8;
    $def[1] .= "LINE:$n#$line_colors[$ii]:\"$n\" ";
    $def[1] .= "GPRINT:$n:LAST:\"Cur\: %.0lf C \" ";
    $def[1] .= "GPRINT:$n:AVERAGE:\"Avg\: %.0lf C \" ";
    $def[1] .= "GPRINT:$n:MIN:\"Min\: %.0lf C \" ";
    $def[1] .= "GPRINT:$n:MAX:\"Max\: %.0lf C \\n\" ";
}

$def[1] .= "HRULE:$WARN[1]#ffe000:\"Warning at $WARN[1] C\" ";
$def[1] .= "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[1] C \\n\" ";

?>
