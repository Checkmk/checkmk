<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The number of data source various due to different
# settings (such as averaging). We rather work with names
# than with numbers.
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n]    = "$RRDFILE[$i]:$DS[$i]:MAX";
    $RRDAVG[$n] = "$RRDFILE[$i]:$DS[$i]:AVERAGE";
    $WARN[$n]   = $WARN[$i];
    $CRIT[$n]   = $CRIT[$i];
    $MIN[$n]    = $MIN[$i];
    $MAX[$n]    = $MAX[$i];
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
  . "DEF:inavg=$RRDAVG[in] "
  . "DEF:outavg=$RRDAVG[out] "
  . "CDEF:inmbavg=inavg,1048576,/ "
  . "CDEF:outmbavg=outavg,1048576,/ "
  . "AREA:inmb#60a020:\"in       \" "
  . "GPRINT:inmb:LAST:\"%5.3lf MB/s last\" "
  . "GPRINT:inmbavg:AVERAGE:\"%5.3lf MB/s avg\" "
  . "GPRINT:inmb:MAX:\"%5.3lf MB/s max\\n\" "
  . "CDEF:out_draw=outmb,-1,* "
  . "AREA:out_draw#2060a0:\"out      \" "
  . "GPRINT:outmb:LAST:\"%5.3lf MB/s last\" "
  . "GPRINT:outmbavg:AVERAGE:\"%5.3lf MB/s avg\" "
  . "GPRINT:outmb:MAX:\"%5.3lf MB/s max\\n\" "
  ;

if (isset($RRD['in_avg'])) {
$def[1] .= ""
  . "DEF:inaverage=$RRD[in_avg] "
  . "DEF:outaverage=$RRD[out_avg] "
  . "CDEF:inaveragemb=inaverage,1048576,/ "
  . "CDEF:outaveragemb=outaverage,1048576,/ "
  . "DEF:inaverage_avg=$RRDAVG[in_avg] "
  . "DEF:outaverage_avg=$RRDAVG[out_avg] "
  . "CDEF:inaveragemb_avg=inaverage_avg,1048576,/ "
  . "CDEF:outaveragemb_avg=outaverage_avg,1048576,/ "
  . "CDEF:outaveragemb_draw=outaverage,-1048576,/ "
  . "LINE:inaveragemb_avg#a0d040:\"in (avg) \" "
  . "GPRINT:inaveragemb:LAST:\"%5.3lf MB/s last\" "
  . "GPRINT:inaveragemb_avg:AVERAGE:\"%5.3lf MB/s avg\" "
  . "GPRINT:inaveragemb:MAX:\"%5.3lf MB/s max\\n\" "
  . "LINE:outaveragemb_draw#40a0d0:\"out (avg)\" "
  . "GPRINT:outaveragemb:LAST:\"%5.3lf MB/s last\" "
  . "GPRINT:outaveragemb_avg:AVERAGE:\"%5.3lf MB/s avg\" "
  . "GPRINT:outaveragemb:MAX:\"%5.3lf MB/s max\\n\" "
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
  . "DEF:inavg=$RRDAVG[rxframes] "
  . "DEF:outavg=$RRDAVG[txframes] "
  . "AREA:in#a0d040:\"in       \" "
  . "GPRINT:in:LAST:\"%5.1lf/s last\" "
  . "GPRINT:inavg:AVERAGE:\"%5.1lf/s avg\" "
  . "GPRINT:in:MAX:\"%5.1lf/s max\\n\" "
  . "CDEF:out_draw=out,-1,* "
  . "AREA:out_draw#40a0d0:\"out      \" "
  . "GPRINT:out:LAST:\"%5.1lf/s last\" "
  . "GPRINT:outavg:AVERAGE:\"%5.1lf/s avgargs\" "
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
