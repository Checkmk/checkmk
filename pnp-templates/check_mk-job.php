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

// Make data sources available via names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

#
# Excecution time
#

$ds_name[1] = "Job Duration";
$opt[1] = "--vertical-label 'Duration (min)' -l0 --title \"Duration for $hostname / $servicedesc\" ";

$def[1] = "DEF:sec=".$RRD['real_time']." ";

$def[1] .= "CDEF:total_minutes=sec,60,/ ";

$def[1] .= "CDEF:days=sec,86400,/,FLOOR ";
$def[1] .= "CDEF:day_rest=sec,86400,% ";
$def[1] .= "CDEF:hours=day_rest,3600,/,FLOOR ";
$def[1] .= "CDEF:hour_rest=day_rest,3600,% ";
$def[1] .= "CDEF:minutes=hour_rest,60,/,FLOOR ";
$def[1] .= "CDEF:seconds=hour_rest,60,% ";

$def[1] .= "AREA:total_minutes#80f000:\"Duration (Last)\" ";
$def[1] .= "LINE:total_minutes#408000 ";
$def[1] .= "GPRINT:days:LAST:\"%2.0lf days\g\" ";
$def[1] .= "GPRINT:hours:LAST:\"%2.0lf hours\g\" ";
$def[1] .= "GPRINT:minutes:LAST:\"%2.0lf min\g\" ";
$def[1] .= "GPRINT:seconds:LAST:\"%2.2lf sec\" ";

#
# CPU time
#

$ds_name[2] = "CPU Time";
$opt[2] = "--vertical-label 'CPU Time' -l0  -u 100 --title \"CPU Time for $hostname / $servicedesc\" ";
$def[2] =  "DEF:user=".$RRD['user_time']." " ;
$def[2] .= "DEF:system=".$RRD['system_time']." " ;
$def[2] .= "CDEF:sum=user,system,+ ";
$def[2] .= "CDEF:idle=100,sum,- ";

$def[2] .= "AREA:system#ff6000:\"System\" " 
         . "GPRINT:system:LAST:\"%2.1lf%%  \" " 
         . "AREA:user#60f020:\"User\":STACK " 
         . "GPRINT:user:LAST:\"%2.1lf%%  \" " 
         . "LINE:sum#004080:\"Total\" " 
         . "GPRINT:sum:LAST:\"%2.1lf%%  \\n\" ";

#
# Disk IO
#

$ds_name[3] = "Disk IO";
$opt[3] = "--vertical-label 'Throughput (MB/s)' -X0  --title \"Disk throughput $hostname / $servicedesc\" ";
$def[3] = "HRULE:0#a0a0a0 "
        . "DEF:read=".$RRD['reads']." "
        . "CDEF:read_mb=read,1048576,/ "
        . "AREA:read_mb#40c080:\"Read \" "
        . "GPRINT:read_mb:LAST:\"%8.1lf MB/s last\" "
        . "GPRINT:read_mb:AVERAGE:\"%6.1lf MB/s avg\" "
        . "GPRINT:read_mb:MAX:\"%6.1lf MB/s max\\n\" ";

$def[3] .= "DEF:write=".$RRD['writes']." "
         . "CDEF:write_mb=write,1048576,/ "
         . "CDEF:write_mb_neg=write_mb,-1,* "
         . "AREA:write_mb_neg#4080c0:\"Write  \" "
         . "GPRINT:write_mb:LAST:\"%6.1lf MB/s last\" "
         . "GPRINT:write_mb:AVERAGE:\"%6.1lf MB/s avg\" "
         . "GPRINT:write_mb:MAX:\"%6.1lf MB/s max\\n\" ";

#
# Context Switches
#

$ds_name[4] = "Context Switches";
$opt[4] = " --vertical-label \"Switches / sec\" --title \"Context Switches $hostname / $servicedesc\" ";

$def[4] = "DEF:sec=".$RRD['real_time']." ";
$def[4] .= "DEF:vol=".$RRD['vol_context_switches']. " ";
$def[4] .= "DEF:invol=".$RRD['invol_context_switches']. " ";
$def[4] .= "CDEF:vol_persec=vol,sec,/ ";
$def[4] .= "CDEF:invol_persec=invol,sec,/ ";

$def[4] .= "AREA:vol_persec#48C4EC:\"Voluntary\:\" ";
$def[4] .= "LINE1:vol_persec#1598C3:\"\" ";
$def[4] .= "GPRINT:vol_persec:LAST:\"  %8.2lf/s last\\n\" ";

$def[4] .= "AREA:invol_persec#7648EC:\"Involuntary\:\":STACK ";
$def[4] .= "LINE1:0#4D18E4:\"\":STACK ";
$def[4] .= "GPRINT:invol_persec:LAST:\"%8.2lf/s last\\n\" ";
?>
