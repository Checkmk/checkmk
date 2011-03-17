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

$parts = explode("_", $servicedesc);
$disk = $parts[2];

$opt[1] = "--vertical-label 'Throughput (MB/s)' -X0  --title \"Disk throughput $hostname / $disk\" ";

$def[1]  = 
           "HRULE:0#a0a0a0 ".
# read
           "DEF:read=$RRDFILE[1]:$DS[1]:MAX ".
           "CDEF:read_mb=read,1048576,/ ".
           "AREA:read_mb#40c080:\"Read \" ".
           "GPRINT:read_mb:LAST:\"%6.1lf MByte/s last\" ".
           "GPRINT:read_mb:AVERAGE:\"%6.1lf MByte/s avg\" ".
           "GPRINT:read_mb:MAX:\"%6.1lf MByte/s max\\n\" ";

# read average
if (isset($DS[3])) {
    $def[1] .= 
           "DEF:read_avg=$RRDFILE[3]:$DS[3]:MAX ".
           "CDEF:read_avg_mb=read_avg,1048576,/ ".
           "LINE:read_avg_mb#202020 ";
}

# write
$def[1] .=
           "DEF:write=$RRDFILE[2]:$DS[2]:MAX ".
           "CDEF:write_mb=write,1048576,/ ".
           "CDEF:write_mb_neg=write_mb,-1,* ".
           "AREA:write_mb_neg#4080c0:Write ".
           "GPRINT:write_mb:LAST:\"%6.1lf MByte/s last\" ".
           "GPRINT:write_mb:AVERAGE:\"%6.1lf MByte/s avg\" ".
           "GPRINT:write_mb:MAX:\"%6.1lf MByte/s max\\n\" ".
           "";

# write average
if (isset($DS[3])) {
    $def[1] .= 
           "DEF:write_avg=$RRDFILE[4]:$DS[4]:MAX ".
           "CDEF:write_avg_mb=write_avg,1048576,/ ".
           "CDEF:write_avg_mb_neg=write_avg_mb,-1,* ".
           "LINE:write_avg_mb_neg#202020 ";
}
?>
