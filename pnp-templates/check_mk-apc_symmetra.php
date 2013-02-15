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

$opt[1] = "--vertical-label \"Celsius\" -l 0 -u 60 --title \"Battery temperature\" ";

$color = sprintf("ff%02x80", $ACT[2] * 3, $ACT[2] * 2);

$def[1] = "DEF:var1=$RRDFILE[2]:$DS[2]:MAX ";
$def[1] .= "AREA:var1#$color:\"Temperature\:\" ";
$def[1] .= "GPRINT:var1:LAST:\"%2.0lfC\" ";
$def[1] .= "LINE1:var1#800040:\"\" ";
$def[1] .= "GPRINT:var1:MAX:\"(Max\: %2.0lfC,\" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"Avg\: %2.0lfC)\" ";
$def[1] .= "HRULE:$CRIT[2]#FF0000:\"Critical\: $CRIT[2]C\" ";

$opt[2] = "--vertical-label \"Percent\" -l 0 -u 100 --title \"Battery Capacity\" ";
$def[2] = "DEF:var2=$RRDFILE[1]:$DS[1]:MIN ";
$def[2] .= "AREA:var2#80e0c0:\"Capacity\:\" ";
$def[2] .= "GPRINT:var2:LAST:\"%2.0lf%%\" ";
$def[2] .= "LINE1:var2#008040:\"\" ";
$def[2] .= "GPRINT:var2:MAX:\"(Max\: %2.0lf%%,\" ";
$def[2] .= "GPRINT:var2:AVERAGE:\"Avg\: %2.0lf%%)\" ";
$def[2] .= "HRULE:$CRIT[1]#FF0000:\"Critical\: $CRIT[1]%\" ";

$opt[3] = "--vertical-label \"Ampere\" -l -0 --title \"Currencies\" ";
$def[3] = "DEF:batcur=$RRDFILE[3]:$DS[3]:MAX ";
$def[3] .= "DEF:outcur=$RRDFILE[5]:$DS[5]:MAX ";
$def[3] .= "LINE:batcur#c0c000:\"Battery Currency\:\" ";
$def[3] .= "GPRINT:batcur:LAST:\"%2.0lfA\" ";
$def[3] .= "LINE:outcur#00c0c0:\"Output Currency\:\" ";
$def[3] .= "GPRINT:outcur:LAST:\"%2.0lfA\" ";

$opt[4] = "--vertical-label \"Volt\" -l 0 -u 250 --title \"Output Voltage\" ";
$def[4] = "DEF:volt=$RRDFILE[4]:$DS[4]:MIN ";
$def[4] .= "GPRINT:volt:LAST:\"%2.0lfV\" ";
$def[4] .= "LINE1:volt#408040:\"\" ";
$def[4] .= "GPRINT:volt:MIN:\"(min\: %2.0lfV,\" ";
$def[4] .= "GPRINT:volt:AVERAGE:\"avg\: %2.0lfV)\" ";
$def[4] .= "HRULE:$CRIT[4]#FF0000:\"Critical\: $CRIT[4]V\" ";

?>
