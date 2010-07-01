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
$bandwidth = $MAX[1] / 1048576.0;
$ds_name[1] = 'Used bandwidth';
$opt[1] = "--vertical-label \"MB/sec\" -X0 -b 1024 -l -1 -u 1 --title \"Used bandwidth $hostname / $servicedesc\" ";
$def[1] = 
  "HRULE:0#c0c0c0 ".
  "HRULE:$bandwidth#808080:\"Port speed\:  " . sprintf("%.1f", $bandwidth) . " MB/s\\n\" ".
  "HRULE:-$bandwidth#808080: ".
  "DEF:inbytes=$RRDFILE[1]:$DS[1]:MAX ".
  "DEF:outbytes=$RRDFILE[6]:$DS[6]:MAX ".
  "CDEF:inmb=inbytes,1048576,/ ".
  "CDEF:outmb=outbytes,1048576,/ ".
  "CDEF:minusoutmb=0,outmb,- ".
  "AREA:inmb#00e060:\"in         \" ".
  "GPRINT:inmb:LAST:\"%5.1lf MB/s last\" ".
  "GPRINT:inmb:AVERAGE:\"%5.1lf MB/s avg\" ".
  "GPRINT:inmb:MAX:\"%5.1lf MB/s max\\n\" ".
  "AREA:minusoutmb#0080e0:\"out        \" ".
  "GPRINT:outmb:LAST:\"%5.1lf MB/s last\" ".
  "GPRINT:outmb:AVERAGE:\"%5.1lf MB/s avg\" ".
  "GPRINT:outmb:MAX:\"%5.1lf MB/s max\\n\" ";

# Graph 2: packets
$ds_name[2] = 'Packets';
$opt[2] = "--vertical-label \"packets/sec\" -b 1024 --title \"Packets $hostname / $servicedesc\" ";
$def[2] =
  "HRULE:0#c0c0c0 ".
  "DEF:inu=$RRDFILE[2]:$DS[2]:MAX ".
  "DEF:innu=$RRDFILE[3]:$DS[3]:MAX ".
  "AREA:inu#00ffc0:\"in unicast \" ".
  "AREA:innu#00c080:\"in broadcast/multicast\\n\":STACK ".
  "DEF:outu=$RRDFILE[2]:$DS[2]:MAX ".
  "DEF:outnu=$RRDFILE[3]:$DS[3]:MAX ".
  "CDEF:minusoutu=0,outu,- ".
  "CDEF:minusoutnu=0,outnu,- ".
  "AREA:minusoutu#00c0ff:\"out unicast\" ".
  "AREA:minusoutnu#0080c0:\"out broadcast/multicast\\n\":STACK ";

# Graph 3: errors and discards
$ds_name[3] = 'Errors and discards';
$opt[3] = "--vertical-label \"packets/sec\" -X0 -b 1024 --title \"Problems $hostname / $servicedesc\" ";
$def[3] =
  "HRULE:0#c0c0c0 ".
  "DEF:inerr=$RRDFILE[4]:$DS[4]:MAX ".
  "DEF:indisc=$RRDFILE[5]:$DS[5]:MAX ".
  "AREA:inerr#ff0000:\"in errors \" ".
  "AREA:indisc#ff8000:\"in discards\\n\":STACK ".
  "DEF:outerr=$RRDFILE[9]:$DS[9]:MAX ".
  "DEF:outdisc=$RRDFILE[10]:$DS[10]:MAX ".
  "CDEF:minusouterr=0,outerr,- ".
  "CDEF:minusoutdisc=0,outdisc,- ".
  "AREA:minusouterr#ff0080:\"out errors\" ".
  "AREA:minusoutdisc#ff8080:\"out discards\\n\":STACK ";
?>
