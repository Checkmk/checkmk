<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

