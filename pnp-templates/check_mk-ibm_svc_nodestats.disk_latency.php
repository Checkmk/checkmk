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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

if (isset($DS[2])) {

    // Make data sources available via names
    $RRD = array();
    foreach ($NAME as $i => $n) {
        $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
        $WARN[$n] = $WARN[$i];
        $CRIT[$n] = $CRIT[$i];
        $MIN[$n]  = $MIN[$i];
        $MAX[$n]  = $MAX[$i];
    }

    $opt[1] = "--vertical-label 'ms' -X0  --title \"$hostname / $servicedesc\" ";

    $def[1]  =
               "HRULE:0#a0a0a0 ".
    # read
               "DEF:read=$RRD[read_latency] ".
               "AREA:read#40c080:\"Latency for read \" ".
               "GPRINT:read:LAST:\"%8.0lf ms last\" ".
               "GPRINT:read:AVERAGE:\"%6.0lf ms avg\" ".
               "GPRINT:read:MAX:\"%6.0lf ms max\\n\" ";

    # write
    $def[1] .=
               "DEF:write=$RRD[write_latency] ".
               "CDEF:write_neg=write,-1,* ".
               "AREA:write_neg#4080c0:\"Latency for write  \"  ".
               "GPRINT:write:LAST:\"%6.0lf ms last\" ".
               "GPRINT:write:AVERAGE:\"%6.0lf ms avg\" ".
               "GPRINT:write:MAX:\"%6.0lf ms max\\n\" ".
               "";
}

