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

setlocale(LC_ALL, 'C');

# Performance data from check:
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

# Determine if Bit or Byte. Bit is signalled via a min value of 0.0
# in the 11th performance value.
if (!strcmp($MIN[11], "0.0")) {
    $unit = "Bit";
    $unit_multiplier = 8;
    $base = 1000; // Megabit is 1000 * 1000
}
else {
    $unit = "B";
    $unit_multiplier = 1;
    $base = 1000; // Megabyte is 1000 * 1000
}

# Convert bytes to bits if neccessary
$bandwidth = $MAX[1]  * $unit_multiplier;
$warn      = $WARN[1] * $unit_multiplier;
$crit      = $CRIT[1] * $unit_multiplier;

# Now choose a convenient scale, based on the known bandwith of
# the interface, and break down bandwidth, warn and crit by that
# scale.
$bwuom = ' ';
if ($bandwidth > $base * $base * $base) {
    $scale = $base * $base * $base;
    $bwuom = 'G';
}
elseif ($bandwidth > $base * $base) {
    $scale = $base * $base;
    $bwuom = 'M';
}
elseif ($bandwidth > $base) {
    $scale = $base;
    $bwuom = 'k';
}
else {
    $scale = 1;
    $bwuom = ' ';
}

$warn      /= $scale;
$crit      /= $scale;
$bandwidth /= $scale;

$vertical_label_name = $bwuom . $unit . "/sec";

$range = min(10, $bandwidth);


$bandwidthInfo = "";
if ($bandwidth > 0){
    $bandwidthInfo = " at " . sprintf("%.1f", $bandwidth) . " ${bwuom}${unit}/s";
}
$ds_name[1] = 'Used bandwidth';
$opt[1] = "--vertical-label \"$vertical_label_name\" -l -$range -u $range -X0 -b 1024 --title \"Used bandwidth $hostname / $servicedesc$bandwidthInfo\" ";
$def[1] =
  "HRULE:0#c0c0c0 ";
if ($bandwidth)
      $def[1] .= "HRULE:$bandwidth#808080:\"Port speed\:  " . sprintf("%10.1f", $bandwidth) . " ".$bwuom."$unit/s\\n\" ".
                 "HRULE:-$bandwidth#808080: ";
if ($warn)
   $def[1] .= "HRULE:$warn#ffff00:\"Warning\:  " . sprintf("%13.1f", $warn) . " ".$bwuom."$unit/s\\n\" ".
              "HRULE:-$warn#ffff00: ";
if ($crit)
   $def[1] .= "HRULE:$crit#ff0000:\"Critical\: " . sprintf("%13.1f", $crit) . " ".$bwuom."$unit/s\\n\" ".
              "HRULE:-$crit#ff0000: ";

  $def[1] .= "".
  # incoming
  "DEF:inbytes=$RRDFILE[1]:$DS[1]:MAX ".
  "CDEF:intraffic=inbytes,$unit_multiplier,* ".
  "CDEF:inmb=intraffic,$scale,/ ".
  "AREA:inmb#00e060:\"in            \" ".
  "GPRINT:intraffic:LAST:\"%7.1lf %s$unit/s last\" ".
  "GPRINT:intraffic:AVERAGE:\"%7.1lf %s$unit/s avg\" ".
  "GPRINT:intraffic:MAX:\"%7.1lf %s$unit/s max\\n\" ".
  "VDEF:inperc=intraffic,95,PERCENTNAN ".
  "VDEF:inpercmb=inmb,95,PERCENTNAN ".
  "LINE:inpercmb#008f00:\"95% percentile\" ".
  "GPRINT:inperc:\"%7.1lf %s$unit/s\\n\" ".

  # outgoing
  "DEF:outbytes=$RRDFILE[6]:$DS[6]:MAX ".
  "CDEF:outtraffic=outbytes,$unit_multiplier,* ".
  "CDEF:minusouttraffic=outtraffic,-1,* ".
  "CDEF:outmb=outtraffic,$scale,/ ".
  "CDEF:minusoutmb=0,outmb,- ".
  "AREA:minusoutmb#0080e0:\"out           \" ".
  "GPRINT:outtraffic:LAST:\"%7.1lf %s$unit/s last\" ".
  "GPRINT:outtraffic:AVERAGE:\"%7.1lf %s$unit/s avg\" ".
  "GPRINT:outtraffic:MAX:\"%7.1lf %s$unit/s max\\n\" ".
  "VDEF:outperc=minusouttraffic,5,PERCENTNAN ".
  "VDEF:outpercmb=minusoutmb,5,PERCENTNAN ".
  "LINE:outpercmb#00008f:\"95% percentile\" ".
  "GPRINT:outperc:\"%7.1lf %s$unit/s\\n\" ".

  "";

if (isset($DS[12])) {
  $def[1] .=
  "DEF:inbytesa=$RRDFILE[12]:$DS[12]:MAX ".
  "DEF:outbytesa=$RRDFILE[13]:$DS[13]:MAX ".
  "CDEF:intraffica=inbytesa,$unit_multiplier,* ".
  "CDEF:outtraffica=outbytesa,$unit_multiplier,* ".
  "CDEF:inmba=intraffica,$scale,/ ".
  "CDEF:outmba=outtraffica,$scale,/ ".
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
$ds_name[2] = 'Packets';
$opt[2] = "--vertical-label \"packets/sec\" --title \"Packets $hostname / $servicedesc\" ";
$def[2] =
  # ingoing
  "HRULE:0#c0c0c0 ".
  "DEF:inu=$RRDFILE[2]:$DS[2]:MAX ".
  "DEF:innu=$RRDFILE[3]:$DS[3]:MAX ".
  "CDEF:in=inu,innu,+ ".
  "AREA:inu#00ffc0:\"in unicast             \" ".
  "GPRINT:inu:LAST:\"%9.1lf/s last \" ".
  "GPRINT:inu:AVERAGE:\"%9.1lf/s avg \" ".
  "GPRINT:inu:MAX:\"%9.1lf/s max\\n\" ".
  "AREA:innu#00c080:\"in broadcast/multicast \":STACK ".
  "GPRINT:innu:LAST:\"%9.1lf/s last \" ".
  "GPRINT:innu:AVERAGE:\"%9.1lf/s avg \" ".
  "GPRINT:innu:MAX:\"%9.1lf/s max\\n\" ".
  "VDEF:inperc=in,95,PERCENTNAN ".
  "LINE:inperc#00cf00:\"in 95% percentile      \" ".
  "GPRINT:inperc:\"%9.1lf/s\\n\" ".

  # outgoing
  "DEF:outu=$RRDFILE[7]:$DS[7]:MAX ".
  "DEF:outnu=$RRDFILE[8]:$DS[8]:MAX ".
  "CDEF:minusoutu=0,outu,- ".
  "CDEF:minusoutnu=0,outnu,- ".
  "CDEF:minusout=minusoutu,minusoutnu,+ ".
  "AREA:minusoutu#00c0ff:\"out unicast            \" ".
  "GPRINT:outu:LAST:\"%9.1lf/s last \" ".
  "GPRINT:outu:AVERAGE:\"%9.1lf/s avg \" ".
  "GPRINT:outu:MAX:\"%9.1lf/s max\\n\" ".
  "AREA:minusoutnu#0080c0:\"out broadcast/multicast\":STACK ".
  "GPRINT:outnu:LAST:\"%9.1lf/s last \" ".
  "GPRINT:outnu:AVERAGE:\"%9.1lf/s avg \"  ".
  "GPRINT:outnu:MAX:\"%9.1lf/s max\\n\" ".
  "VDEF:outperc=minusout,5,PERCENTNAN ".
  "LINE:outperc#0000cf:\"out 95% percentile     \" ".
  "GPRINT:outperc:\"%9.1lf/s\\n\" ".
  "";

# Graph 3: errors and discards
$ds_name[3] = 'Errors and discards';
$opt[3] = "--vertical-label \"packets/sec\" -X0 --title \"Problems $hostname / $servicedesc\" ";
$def[3] =
  "HRULE:0#c0c0c0 ".
  "DEF:inerr=$RRDFILE[5]:$DS[5]:MAX ".
  "DEF:indisc=$RRDFILE[4]:$DS[4]:MAX ".
  "AREA:inerr#ff0000:\"in errors               \" ".
  "GPRINT:inerr:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:inerr:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:inerr:MAX:\"%7.2lf/s max\\n\" ".
  "AREA:indisc#ff8000:\"in discards             \":STACK ".
  "GPRINT:indisc:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:indisc:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:indisc:MAX:\"%7.2lf/s max\\n\" ".
  "DEF:outerr=$RRDFILE[10]:$DS[10]:MAX ".
  "DEF:outdisc=$RRDFILE[9]:$DS[9]:MAX ".
  "CDEF:minusouterr=0,outerr,- ".
  "CDEF:minusoutdisc=0,outdisc,- ".
  "AREA:minusouterr#ff0080:\"out errors              \" ".
  "GPRINT:outerr:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:outerr:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:outerr:MAX:\"%7.2lf/s max\\n\" ".
  "AREA:minusoutdisc#ff8080:\"out discards            \":STACK ".
  "GPRINT:outdisc:LAST:\"%7.2lf/s last  \" ".
  "GPRINT:outdisc:AVERAGE:\"%7.2lf/s avg  \" ".
  "GPRINT:outdisc:MAX:\"%7.2lf/s max\\n\" ";
?>
