<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
# outqlen=0;;;;

# Graph 1: used bandwidth
$bitBandwidth = $MAX[1] * 8;
$warn = $WARN[1];
$crit = $CRIT[1];

$bandwidth = $bitBandwidth;
$mByteBandwidth = $MAX[1] / 1000 / 1000;
$mByteWarn      = $WARN[1] / 1000 / 1000;
$mByteCrit      = $CRIT[1] / 1000 / 1000;

$bwuom = '';
$base = 1000;
if($bandwidth > $base * $base * $base) {
	$warn /= $base * $base * $base;
	$crit /= $base * $base * $base;
	$bandwidth /= $base * $base * $base;
	$bwuom = 'G';
} elseif($bandwidth > $base * $base) {
	$warn /= $base * $base;
	$crit /= $base * $base;
	$bandwidth /= $base * $base;
	$bwuom = 'M';
} elseif($bandwidth > $base) {
	$warn /= $base;
	$crit /= $base;
	$bandwidth /= $base;
	$bwuom = 'K';
}

$ds_name[1] = 'Used bandwidth';
$opt[1] = "--vertical-label \"MB/sec\" -X0 -b 1024 --title \"Used bandwidth $hostname / $servicedesc\" ";
$def[1] = 
  "HRULE:0#c0c0c0 ".
  "LINE:$mByteBandwidth#808080:\"Port speed\:  " . sprintf("%.1f", $bandwidth) . " ".$bwuom."Bit/s  \" ".
  "LINE:$mByteWarn#ffff00:\"Warning\:  " . sprintf("%.1f", $warn) . " ".$bwuom."Bit/s  \" ".
  "LINE:$mByteCrit#ff0000:\"Critical\:  " . sprintf("%.1f", $crit) . " ".$bwuom."Bit/s\\n\" ".
  "LINE:-$mByteBandwidth#808080: ".
  "DEF:inbytes=$RRDFILE[1]:$DS[1]:MAX ".
  "DEF:outbytes=$RRDFILE[6]:$DS[6]:MAX ".
  "CDEF:inmb=inbytes,1048576,/ ".
  "CDEF:outmb=outbytes,1048576,/ ".
  "CDEF:minusoutmb=0,outmb,- ".
  "AREA:inmb#00e060:\"in         \" ".
  "GPRINT:inbytes:LAST:\"%5.1lf %sB/s last\" ".
  "GPRINT:inbytes:AVERAGE:\"%5.1lf %sB/s avg\" ".
  "GPRINT:inbytes:MAX:\"%5.1lf %sB/s max\\n\" ".
  "AREA:minusoutmb#0080e0:\"out        \" ".
  "GPRINT:outbytes:LAST:\"%5.1lf %sB/s last\" ".
  "GPRINT:outbytes:AVERAGE:\"%5.1lf %sB/s avg\" ".
  "GPRINT:outbytes:MAX:\"%5.1lf %sB/s max\\n\" ";

# Graph 2: packets
$ds_name[2] = 'Packets';
$opt[2] = "--vertical-label \"packets/sec\" --title \"Packets $hostname / $servicedesc\" ";
$def[2] =
  "HRULE:0#c0c0c0 ".
  "DEF:inu=$RRDFILE[2]:$DS[2]:MAX ".
  "DEF:innu=$RRDFILE[3]:$DS[3]:MAX ".
  "AREA:inu#00ffc0:\"in unicast             \" ".
  "GPRINT:inu:LAST:\"%5.2lf/s last\" ".
  "GPRINT:inu:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:inu:MAX:\"%5.2lf/s max\\n\" ".
  "AREA:innu#00c080:\"in broadcast/multicast \":STACK ".
  "GPRINT:innu:LAST:\"%5.2lf/s last\" ".
  "GPRINT:innu:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:innu:MAX:\"%5.2lf/s max\\n\" ".
  "DEF:outu=$RRDFILE[2]:$DS[2]:MAX ".
  "DEF:outnu=$RRDFILE[3]:$DS[3]:MAX ".
  "CDEF:minusoutu=0,outu,- ".
  "CDEF:minusoutnu=0,outnu,- ".
  "AREA:minusoutu#00c0ff:\"out unicast            \" ".
  "GPRINT:outu:LAST:\"%5.2lf/s last\" ".
  "GPRINT:outu:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:outu:MAX:\"%5.2lf/s max\\n\" ".
  "AREA:minusoutnu#0080c0:\"out broadcast/multicast\":STACK ".
  "GPRINT:outnu:LAST:\"%5.2lf/s last\" ".
  "GPRINT:outnu:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:outnu:MAX:\"%5.2lf/s max\\n\" ";

# Graph 3: errors and discards
$ds_name[3] = 'Errors and discards';
$opt[3] = "--vertical-label \"packets/sec\" -X0 --title \"Problems $hostname / $servicedesc\" ";
$def[3] =
  "HRULE:0#c0c0c0 ".
  "DEF:inerr=$RRDFILE[4]:$DS[4]:MAX ".
  "DEF:indisc=$RRDFILE[5]:$DS[5]:MAX ".
  "AREA:inerr#ff0000:\"in errors   \" ".
  "GPRINT:inerr:LAST:\"%5.2lf/s last\" ".
  "GPRINT:inerr:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:inerr:MAX:\"%5.2lf/s max\\n\" ".
  "AREA:indisc#ff8000:\"in discards \":STACK ".
  "GPRINT:indisc:LAST:\"%5.2lf/s last\" ".
  "GPRINT:indisc:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:indisc:MAX:\"%5.2lf/s max\\n\" ".
  "DEF:outerr=$RRDFILE[9]:$DS[9]:MAX ".
  "DEF:outdisc=$RRDFILE[10]:$DS[10]:MAX ".
  "CDEF:minusouterr=0,outerr,- ".
  "CDEF:minusoutdisc=0,outdisc,- ".
  "AREA:minusouterr#ff0080:\"out errors  \" ".
  "GPRINT:outerr:LAST:\"%5.2lf/s last\" ".
  "GPRINT:outerr:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:outerr:MAX:\"%5.2lf/s max\\n\" ".
  "AREA:minusoutdisc#ff8080:\"out discards\":STACK ".
  "GPRINT:outdisc:LAST:\"%5.2lf/s last\" ".
  "GPRINT:outdisc:AVERAGE:\"%5.2lf/s avg\" ".
  "GPRINT:outdisc:MAX:\"%5.2lf/s max\\n\" ";
?>
