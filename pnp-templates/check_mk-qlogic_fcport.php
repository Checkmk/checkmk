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
  . "GPRINT:outavg:AVERAGE:\"%5.1lf/s avg\" "
  . "GPRINT:out:MAX:\"%5.1lf/s max\\n\" "
  ;

# 3. GRAPH: ERRORS

$ds_name[3] = 'Error counter';
$opt[3]  = "--vertical-label \"Error counter\" --title \"Problems\" ";
$def[3] = ""
  . "DEF:link_failures=$RRD[link_failures] "
  . "DEF:sync_losses=$RRD[sync_losses] "
  . "DEF:prim_seq_proto_errors=$RRD[prim_seq_proto_errors] "
  . "DEF:invalid_tx_words=$RRD[invalid_tx_words] "
  . "DEF:invalid_crcs=$RRD[invalid_crcs] "
  . "DEF:address_id_errors=$RRD[address_id_errors] "
  . "DEF:link_reset_ins=$RRD[link_reset_ins] "
  . "DEF:link_reset_outs=$RRD[link_reset_outs] "
  . "DEF:ols_ins=$RRD[ols_ins] "
  . "DEF:ols_outs=$RRD[ols_outs] "
  . "DEF:discards=$RRD[discards] "
  . "DEF:c2_fbsy_frames=$RRD[c2_fbsy_frames] "
  . "DEF:c2_frjt_frames=$RRD[c2_frjt_frames] "
  . "LINE1:link_failures#c00000:\"Link Failures        \" "
  . "GPRINT:link_failures:LAST:\"last\: %4.0lf/s    \\n\" "
  . "LINE1:sync_losses#ff8000:\"Sync Losses          \" "
  . "GPRINT:sync_losses:LAST:\"last\: %4.0lf/s\\n\" "
  . "LINE1:prim_seq_proto_errors#ff0080:\"PrimitSeqErrors      \" "
  . "GPRINT:prim_seq_proto_errors:LAST:\"last\: %4.0lf/s    \\n\" "
  . "LINE1:invalid_tx_words#ffa0a0:\"Invalid TX Words     \" "
  . "GPRINT:invalid_tx_words:LAST:\"last\: %4.0lf/s\\n\" "
  . "LINE1:invalid_crcs#0080FF:\"Invalid CRCs         \" "
  . "GPRINT:invalid_crcs:LAST:\"last\: %4.0lf/s    \\n\" "
  . "LINE1:address_id_errors#8080FF:\"Address ID Errors    \" "
  . "GPRINT:address_id_errors:LAST:\"last\: %4.0lf/s\\n\" "
  . "LINE1:link_reset_ins#0000A0:\"Link Resets In       \" "
  . "GPRINT:link_reset_ins:LAST:\"last\: %4.0lf/s    \\n\" "
  . "LINE1:link_reset_outs#400080:\"Link Resets Out      \" "
  . "GPRINT:link_reset_outs:LAST:\"last\: %4.0lf/s\\n\" "
  . "LINE1:ols_ins#800000:\"Offline Sequences In \" "
  . "GPRINT:ols_ins:LAST:\"last\: %4.0lf/s\\n\" "
  . "LINE1:ols_outs#FF0000:\"Offline Sequences Out\" "
  . "GPRINT:ols_outs:LAST:\"last\: %4.0lf/s    \\n\" "
  . "LINE1:discards#800080:\"Discards             \" "
  . "GPRINT:discards:LAST:\"last\: %4.0lf/s\\n\" "
  . "LINE1:c2_fbsy_frames#0000FF:\"F_BSY frames         \" "
  . "GPRINT:c2_fbsy_frames:LAST:\"last\: %4.0lf/s    \\n\" "
  . "LINE1:c2_frjt_frames#408080:\"F_RJT frames         \" "
  . "GPRINT:c2_frjt_frames:LAST:\"last\: %4.0lf/s\\n\" "
  ;
?>


