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


# 1. GRAPH: THROUGHPUT IN MB/s

$ds_name[1] = 'Traffic';
$opt[1]  = "--vertical-label \"MByte/sec\" -X0 -b 1024 --title \"Traffic for $hostname / $servicedesc\" ";

$def[1] = ""
  . "HRULE:0#c0c0c0 "
  . "DEF:in=$RRD[in] "
  . "DEF:out=$RRD[out] "
  . "CDEF:inmb=in,1048576,/ "
  . "CDEF:outmb=out,1048576,/ "
  . "AREA:inmb#60a020:\"in       \" "
  . "GPRINT:inmb:LAST:\"%5.1lf MB/s last\" "
  . "GPRINT:inmb:AVERAGE:\"%5.1lf MB/s avg\" "
  . "GPRINT:inmb:MAX:\"%5.1lf MB/s max\\n\" "
  . "CDEF:out_draw=outmb,-1,* "
  . "AREA:out_draw#2060a0:\"out      \" "
  . "GPRINT:outmb:LAST:\"%5.1lf MB/s last\" "
  . "GPRINT:outmb:AVERAGE:\"%5.1lf MB/s avg\" "
  . "GPRINT:outmb:MAX:\"%5.1lf MB/s max\\n\" "
  ;

if (isset($RRD['in_avg'])) {
$def[1] .= ""
  . "DEF:inavg=$RRD[in_avg] "
  . "DEF:outavg=$RRD[out_avg] "
  . "CDEF:inavgmb=inavg,1048576,/ "
  . "CDEF:outavgmb=outavg,1048576,/ "
  . "CDEF:outavgmbdraw=outavg,-1048576,/ "
  . "LINE:inavgmb#a0d040:\"in (avg) \" "
  . "GPRINT:inavgmb:LAST:\"%5.1lf MB/s last\" "
  . "GPRINT:inavgmb:AVERAGE:\"%5.1lf MB/s avg\" "
  . "GPRINT:inavgmb:MAX:\"%5.1lf MB/s max\\n\" "
  . "LINE:outavgmbdraw#40a0d0:\"out (avg)\" "
  . "GPRINT:outavgmb:LAST:\"%5.1lf MB/s last\" "
  . "GPRINT:outavgmb:AVERAGE:\"%5.1lf MB/s avg\" "
  . "GPRINT:outavgmb:MAX:\"%5.1lf MB/s max\\n\" "
  ;
}

if ($WARN['in']) {
   $def[1] .= "HRULE:$WARN[in]#ffff00:\"Warning (in)\" ";
   $def[1] .= "HRULE:-$WARN[out]#ffff00:\"Warning (out)\" ";
}
if ($CRIT['in']) {
   $def[1] .= "HRULE:$CRIT[in]#ff0000:\"Critical (in)\" ";
   $def[1] .= "HRULE:-$CRIT[out]#ff0000:\"Critical (out)\" ";
}
if ($MAX['in'])  {
   $speedmb = $MAX['in'] / 1048576.0;
   $speedtxt = sprintf("%.1f MB/s", $speedmb);
   $def[1] .= "HRULE:$speedmb#ff80c0:\"Portspeed\: $speedtxt\" ";
   $def[1] .= "HRULE:-$speedmb#ff80c0 ";
   # $opt[1] .= " -u $speedmb -l -$speedmb";
}

# 2. GRAPH: FRAMES
$ds_name[2] = 'Frames';
$opt[2]  = "--vertical-label \"Frames/sec\" -b 1024 --title \"Frames per second\" ";
$def[2] = ""
  . "HRULE:0#c0c0c0 "
  . "DEF:in=$RRD[rxframes] "
  . "DEF:out=$RRD[txframes] "
  . "AREA:in#a0d040:\"in       \" "
  . "GPRINT:in:LAST:\"%5.1lf/s last\" "
  . "GPRINT:in:AVERAGE:\"%5.1lf/s avg\" "
  . "GPRINT:in:MAX:\"%5.1lf/s max\\n\" "
  . "CDEF:out_draw=out,-1,* "
  . "AREA:out_draw#40a0d0:\"out      \" "
  . "GPRINT:out:LAST:\"%5.1lf/s last\" "
  . "GPRINT:out:AVERAGE:\"%5.1lf/s avg\" "
  . "GPRINT:out:MAX:\"%5.1lf/s max\\n\" "
  ;

# 3. GRAPH: ERRORS

$ds_name[3] = 'Error counter';
$opt[3]  = "--vertical-label \"Error counter\" --title \"Problems\" ";
$def[3] = ""
  . "DEF:rxcrcs=$RRD[rxcrcs] "
  . "DEF:notxcredits=$RRD[notxcredits] "
  . "DEF:rxencoutframes=$RRD[rxencoutframes] "
  . "DEF:c3discards=$RRD[c3discards] "
  . "LINE1:rxcrcs#c00000:\"CRC Errors      \" "
  . "GPRINT:rxcrcs:LAST:\"last\: %4.0lf/s    \" "
  . "LINE1:notxcredits#ff8000:\"No Tx Credits   \" "
  . "GPRINT:notxcredits:LAST:\"last\: %4.0lf/s\\n\" "
  . "LINE1:rxencoutframes#ff0080:\"ENC-Out Frames  \" "
  . "GPRINT:rxencoutframes:LAST:\"last\: %4.0lf/s    \" "
  . "LINE1:c3discards#ffa0a0:\"Class 3 Discards\" "
  . "GPRINT:c3discards:LAST:\"last\: %4.0lf/s\\n\" "
  ;
?>
