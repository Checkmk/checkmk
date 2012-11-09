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

// new version of diskstat
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

    $parts = explode("_", $servicedesc);
    $disk = $parts[2];

    $opt[1] = "--vertical-label 'Throughput (MB/s)' -X0  --title \"Disk throughput $hostname / $disk\" ";

    $def[1]  = 
               "HRULE:0#a0a0a0 ".
    # read
               "DEF:read=$RRD[read] ".
               "CDEF:read_mb=read,1048576,/ ".
               "AREA:read_mb#40c080:\"Read \" ".
               "GPRINT:read_mb:LAST:\"%8.1lf MB/s last\" ".
               "GPRINT:read_mb:AVERAGE:\"%6.1lf MB/s avg\" ".
               "GPRINT:read_mb:MAX:\"%6.1lf MB/s max\\n\" ";

    # read average as line in the same graph
    if (isset($RRD["read.avg"])) {
        $def[1] .= 
               "DEF:read_avg=${RRD['read.avg']} ".
               "CDEF:read_avg_mb=read_avg,1048576,/ ".
               "LINE:read_avg_mb#202020 ";
    }

    # write
    $def[1] .=
               "DEF:write=$RRD[write] ".
               "CDEF:write_mb=write,1048576,/ ".
               "CDEF:write_mb_neg=write_mb,-1,* ".
               "AREA:write_mb_neg#4080c0:\"Write  \"  ".
               "GPRINT:write_mb:LAST:\"%6.1lf MB/s last\" ".
               "GPRINT:write_mb:AVERAGE:\"%6.1lf MB/s avg\" ".
               "GPRINT:write_mb:MAX:\"%6.1lf MB/s max\\n\" ".
               "";

    # show levels for read
    if ($WARN['read']) {
        $def[1] .= "HRULE:$WARN[read]#ffd000:\"Warning for read at  " . sprintf("%6.1f", $WARN[1]) . " MB/s  \" ";
        $def[1] .= "HRULE:$CRIT[read]#ff0000:\"Critical for read at  " . sprintf("%6.1f", $CRIT[1]) . " MB/s\\n\" ";
    }

    # show levels for write
    if ($WARN['write']) {
        $def[1] .= "HRULE:-$WARN[write]#ffd000:\"Warning for write at " . sprintf("%6.1f", $WARN[2]) . " MB/s  \" ";
        $def[1] .= "HRULE:-$CRIT[write]#ff0000:\"Critical for write at " . sprintf("%6.1f", $CRIT[2]) . " MB/s\\n\" ";
    }

    # write average
    if (isset($DS["write.avg"])) {
        $def[1] .= 
               "DEF:write_avg=${RRD['write.avg']} ".
               "CDEF:write_avg_mb=write_avg,1048576,/ ".
               "CDEF:write_avg_mb_neg=write_avg_mb,-1,* ".
               "LINE:write_avg_mb_neg#202020 ";
    }

    # latency
    if (isset($RRD["latency"])) {
        $opt[] = "--vertical-label 'Latency (ms)' -X0  --title \"Latency $hostname / $disk\" ";
        $def[] = ""
                . "DEF:latency=$RRD[latency] "
                . "AREA:latency#aaccdd:\"Latency\" "
                . "LINE:latency#7799aa "
                . "GPRINT:latency:LAST:\"%6.1lf ms last\" "
                . "GPRINT:latency:AVERAGE:\"%6.1lf ms avg\" "
                . "GPRINT:latency:MAX:\"%6.1lf ms max\\n\" "
                ;
    }

    # IOs per second
    if (isset($RRD["ios"])) {
        $opt[] = "--vertical-label 'IO Operations / sec' -X0  --title \"IOs/sec $hostname / $disk\" ";
        $def[] = ""
                . "DEF:ios=$RRD[ios] "
                . "AREA:ios#ddccaa:\"ios\" "
                . "LINE:ios#aa9977 "
                . "GPRINT:ios:LAST:\"%6.1lf/sec last\" "
                . "GPRINT:ios:AVERAGE:\"%6.1lf/sec avg\" "
                . "GPRINT:ios:MAX:\"%6.1lf/sec max\\n\" "
                ;
    }

    if (isset($RRD["read_ql"])) {
        $opt[] = "--vertical-label 'Queue Length' -X0 -u10 -l-10 --title \"Queue Length $hostname / $disk\" ";
        $def[] = ""
                . "DEF:read=$RRD[read_ql] "
                . "DEF:write=$RRD[write_ql] "
                . "CDEF:writen=write,-1,* " 
                . "HRULE:0#a0a0a0 "
                . "AREA:read#669a76 "
                . "AREA:writen#517ba5 "
                ;

    }
            
}

// legacy version of diskstat
else {
    $opt[1] = "--vertical-label 'Througput (MByte/s)' -l0  -u 1 --title \"Disk throughput $hostname / $servicedesc\" ";

    $def[1]  = "DEF:kb=$RRDFILE[1]:$DS[1]:AVERAGE " ;
    $def[1] .= "CDEF:mb=kb,1024,/ " ;
    $def[1] .= "AREA:mb#40c080 " ;
               "HRULE:0#a0a0a0 ".
    $def[1] .= "GPRINT:mb:LAST:\"%6.1lf MByte/s last\" " ;
    $def[1] .= "GPRINT:mb:AVERAGE:\"%6.1lf MByte/s avg\" " ;
    $def[1] .= "GPRINT:mb:MAX:\"%6.1lf MByte/s max\\n\" ";
}
?>

