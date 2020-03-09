<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

setlocale(LC_ALL, 'C');

# Performance data from check:
# in=0;;;0;2000000000
# out=0;;;0;2000000000
# rxobjects=0;;;;
# txobjects=0;;;;
# rxcrcs=0;;;;
# rxencoutframes=0;;;;
# c3discards=0;;;;
# notxcredits=0;;;;
#
# in=6864.39071505;0.01;0.1;0;125000000.0
# inucast=48.496962273;0.01;0.1;;
# innucast=4.60122981717;0.01;0.1;;
# indisc=0.0;0.01;0.1;;
# inerr=0.0;0.01;0.1;;
# out=12448.259172;0.01;0.1;0;125000000.0
# outucast=54.9846963152;0.01;0.1;;
# outnucast=10.5828285795;0.01;0.1;;
# outdisc=0.0;0.01;0.1;;
# outerr=0.0;0.01;0.1;;
# outqlen=0;;;;10000000

# Graph 1: used bandwidth

# Determine if Bit or Byte.
# Change multiplier and labels
$unit = "B";
$unit_multiplier = 1;
$vertical_label_name = "MByte/sec";
#if (strcmp($MIN[11], "0.0") == 0) {
#    $unit = "Bit";
#    $unit_multiplier = 8;
#    $vertical_label_name = "MBit/sec";
#}
$bandwidth = $MAX[1]  * $unit_multiplier;
$warn      = $WARN[1] * $unit_multiplier;
$crit      = $CRIT[1] * $unit_multiplier;

# Horizontal lines
$mega        = 1024.0 * 1024.0;
$mBandwidthH = $bandwidth / $mega;
$mWarnH      = $warn      / $mega;
$mCritH      = $crit      / $mega;

# Break down bandwidth, warn and crit
$bwuom = ' ';
$base = 1000;
if($bandwidth > $base * $base * $base) {
	$warn /= $base * $base * $base;
	$crit /= $base * $base * $base;
	$bandwidth /= $base * $base * $base;
	$bwuom = 'G';
} elseif ($bandwidth > $base * $base) {
	$warn /= $base * $base;
	$crit /= $base * $base;
	$bandwidth /= $base * $base;
	$bwuom = 'M';
} elseif ($bandwidth > $base) {
	$warn /= $base;
	$crit /= $base;
	$bandwidth /= $base;
	$bwuom = 'k';
}

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

if ($mBandwidthH < 10)
   $range = $mBandwidthH;
else
   $range = 10.0;

$bandwidthInfo = "";
#if ($bandwidth > 0){
#    $bandwidthInfo = " at bandwidth ${bwuom}${unit}/s";
#}
$ds_name[1] = 'Used bandwidth';
$opt[1] = "--vertical-label \"$vertical_label_name\" -l -$range -u $range -X0 -b 1024 --title \"Used bandwidth $hostname / $servicedesc $bandwidthInfo\" ";
$def[1] =
  "HRULE:0#c0c0c0 ";
  if ($mBandwidthH)
      $def[1] .= "HRULE:$mBandwidthH#808080:\"Port speed\:  " . sprintf("%.1f", $bandwidth) . " ".$bwuom."$unit/s\\n\" ".
                 "HRULE:-$mBandwidthH#808080: ";
   if ($warn)
      $def[1] .= "HRULE:$mWarnH#ffff00:\"Warning\:                " . sprintf("%6.1f", $warn) . " ".$bwuom."$unit/s\\n\" ".
                 "HRULE:-$mWarnH#ffff00: ";
   if ($crit)
      $def[1] .= "HRULE:$mCritH#ff0000:\"Critical\:               " . sprintf("%6.1f", $crit) . " ".$bwuom."$unit/s\\n\" ".
                 "HRULE:-$mCritH#ff0000: ";

  $def[1] .= "".
  # incoming
  "DEF:inbytes=$RRD[in] ".
  "CDEF:intraffic=inbytes,$unit_multiplier,* ".
  "CDEF:inmb=intraffic,1048576,/ ".
  "AREA:inmb#00e060:\"in            \" ".
  "GPRINT:intraffic:LAST:\"%7.1lf %s$unit/s last\" ".
  "GPRINT:intraffic:AVERAGE:\"%7.1lf %s$unit/s avg\" ".
  "GPRINT:intraffic:MAX:\"%7.1lf %s$unit/s max\\n\" ".
  "VDEF:inperc=intraffic,95,PERCENTNAN ".
  "VDEF:inpercmb=inmb,95,PERCENTNAN ".
  "LINE:inpercmb#008f00:\"95% percentile\" ".
  "GPRINT:inperc:\"%7.1lf %s$unit/s\\n\" ".

  # outgoing
  "DEF:outbytes=$RRD[out] ".
  "CDEF:outtraffic=outbytes,$unit_multiplier,* ".
  "CDEF:minusouttraffic=outtraffic,-1,* ".
  "CDEF:outmb=outtraffic,1048576,/ ".
  "CDEF:minusoutmb=0,outmb,- ".
  "AREA:minusoutmb#0080e0:\"out           \" ".
  "GPRINT:outtraffic:LAST:\"%7.1lf %s$unit/s last\" ".
  "GPRINT:outtraffic:AVERAGE:\"%7.1lf %s$unit/s avg\" ".
  "GPRINT:outtraffic:MAX:\"%7.1lf %s$unit/s max\\n\" ".
  "VDEF:outperc=outtraffic,5,PERCENTNAN ".
  "VDEF:outpercmb=minusoutmb,5,PERCENTNAN ".
  "LINE:outpercmb#00008f:\"95% percentile\" ".
  "GPRINT:outperc:\"%7.1lf %s$unit/s\\n\" ".

  "";

# averages
if (isset($DS[9])) {
  $def[1] .=
  "DEF:inbytesa=$RRD[in_avg] ".
  "DEF:outbytesa=$RRD[out_avg] ".
  "CDEF:intraffica=inbytesa,$unit_multiplier,* ".
  "CDEF:outtraffica=outbytesa,$unit_multiplier,* ".
  "CDEF:inmba=intraffica,1048576,/ ".
  "CDEF:outmba=outtraffica,1048576,/ ".
  "CDEF:minusoutmba=0,outmba,- ".
  "LINE:inmba#00a060:\"in (avg)              \" ".
  "GPRINT:intraffica:LAST:\"%6.1lf %s$unit/s last\" ".
  "GPRINT:intraffica:AVERAGE:\"%6.1lf %s$unit/s avg\" ".
  "GPRINT:intraffica:MAX:\"%6.1lf %s$unit/s max\\n\" ".
  "LINE:minusoutmba#0060c0:\"out (avg)             \" ".
  "GPRINT:outtraffica:LAST:\"%6.1lf %s$unit/s last\" ".
  "GPRINT:outtraffica:AVERAGE:\"%6.1lf %s$unit/s avg\" ".
  "GPRINT:outtraffica:MAX:\"%6.1lf %s$unit/s max\\n\" ";
}

# Graph 2: packets
$ds_name[2] = 'Objects';
$opt[2] = "--vertical-label \"objects/sec\" --title \"Objects $hostname / $servicedesc\" ";
$def[2] =
  # rxobjects
  "HRULE:0#c0c0c0 ".
  "DEF:inu=$RRD[rxobjects] ".
  "CDEF:in=inu ".
  "AREA:inu#00ffc0:\"rxobjects         \" ".
  "GPRINT:inu:LAST:\"%9.1lf/s last \" ".
  "GPRINT:inu:AVERAGE:\"%9.1lf/s avg \" ".
  "GPRINT:inu:MAX:\"%9.1lf/s max\\n\" ".
  "VDEF:inperc=in,95,PERCENTNAN ".
  "LINE:inperc#00cf00:\"in 95% percentile \" ".
  "GPRINT:inperc:\"%9.1lf/s\\n\" ".

  # txobjects
  "DEF:outu=$RRD[txobjects] ".
  "CDEF:minusoutu=0,outu,- ".
  "AREA:minusoutu#00c0ff:\"txobjects         \" ".
  "GPRINT:outu:LAST:\"%9.1lf/s last \" ".
  "GPRINT:outu:AVERAGE:\"%9.1lf/s avg \" ".
  "GPRINT:outu:MAX:\"%9.1lf/s max\\n\" ".
  "VDEF:outperc_neg=minusoutu,5,PERCENTNAN ".
  "VDEF:outperc_pos=outu,5,PERCENTNAN ".
  "LINE:outperc_neg#0000cf:\"out 95% percentile\" ".
  "GPRINT:outperc_pos:\"%9.1lf/s\\n\" ".
  "";

# Graph 3: errors and discards
$ds_name[3] = 'Errors and discards';
$opt[3] = "--vertical-label \"errors/sec\" -X0 --title \"Problems $hostname / $servicedesc\" ";
$def[3] =
  "HRULE:0#c0c0c0 ".
  "DEF:crcerr=$RRD[rxcrcs] ".
  "DEF:encout=$RRD[rxencoutframes] ".
  "AREA:crcerr#ff0000:\"crc errors        \" ".
  "GPRINT:crcerr:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:crcerr:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:crcerr:MAX:\"%7.2lf/s max\\n\" ".
  "AREA:encout#ff8000:\"encout frames     \":STACK ".
  "GPRINT:encout:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:encout:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:encout:MAX:\"%7.2lf/s max\\n\" ".
  "DEF:c3discards=$RRD[c3discards] ".
  "DEF:notxcredits=$RRD[notxcredits] ".
  "CDEF:minusc3=0,c3discards,- ".
  "CDEF:minusnotxcredits=0,notxcredits,- ".
  "AREA:minusc3#ff0080:\"c3 discards       \" ".
  "GPRINT:c3discards:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:c3discards:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:c3discards:MAX:\"%7.2lf/s max\\n\" ".
  "AREA:minusnotxcredits#ff8080:\"no tx credits     \":STACK ".
  "GPRINT:notxcredits:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:notxcredits:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:notxcredits:MAX:\"%7.2lf/s max\\n\" ";
?>
