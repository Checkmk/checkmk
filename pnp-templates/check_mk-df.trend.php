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

setlocale(LC_ALL, "POSIX");

$fsname = str_replace("_", "/", substr($servicedesc, 17));
$fstitle = $fsname;

# Hack for windows: replace C// with C:\
if (strlen($fsname) == 3 && substr($fsname, 1, 2) == '//') {
    $fsname = $fsname[0] . "\:\\\\";
    $fstitle = $fsname[0] . ":\\";
}

#
# MB based disk usage trend
#

$opt[1] = "--vertical-label MB -l 0 --title '$hostname: Disk Usage Trend $fstitle' ";

$def[1] = "DEF:var1=$RRDFILE[1]:$DS[1]:MAX "; 
$def[1] .= "HRULE:$MAX[1]#003300:\"Size ($MAX[1] MB) \\n\" ";
$def[1] .= "AREA:var1#00ffc6:\"disk usage trend $fsname\\n\" "; 
$def[1] .= "GPRINT:var1:LAST:\"current\: %6.2lf MB\" ";
$def[1] .= "GPRINT:var1:MAX:\"max\: %6.2lf MB \" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"avg\: %6.2lf MB\" ";

#
# Percent based disk usage trend
#

$opt[2] = "--vertical-label % -l 0 --title '$hostname: Disk Usage Trend $fstitle' ";

$def[2] = "DEF:var1=$RRDFILE[2]:$DS[2]:MAX "; 
$def[2] .= "HRULE:$MAX[2]#003300:\"Size ($MAX[2] MB) \\n\" ";
$def[2] .= "AREA:var1#ff00c6:\"disk usage trend in percent $fsname\\n\" "; 
$def[2] .= "GPRINT:var1:LAST:\"current\: %6.2lf %%\" ";
$def[2] .= "GPRINT:var1:MAX:\"max\: %6.2lf %%\" ";
$def[2] .= "GPRINT:var1:AVERAGE:\"avg\: %6.2lf %%\" ";

#
# Estimated time until no space left (assuming linear growth)
#

$opt[3] = "--vertical-label '' -l 0 --title '$hostname: Time left $fstitle' ";

$def[3] = "DEF:var1=$RRDFILE[3]:$DS[3]:MAX "; 
$def[3] .= "CDEF:days=var1,86400,/ "; 
$def[3] .= "CDEF:hours=var1,86400,%,3600,/ "; 
$def[3] .= "CDEF:min=var1,86400,%,3600,%,60,/ "; 
$def[3] .= "CDEF:sec=var1,86400,%,3600,%,60,% "; 
$def[3] .= "AREA:var1#ff00c6:\"Estimated time left until space filled (assuming linear growth) $fsname\\n\" "; 
foreach(Array('current\:' => 'LAST',
              'max\:    ' => 'MAX',
              'avg\:    ' => 'AVERAGE') AS $name => $item) {
    $def[3] .= "COMMENT:\"$name \" ";
    #$def[3] .= "GPRINT:var1:LAST:\"current\: %6.2lf sec\" ";
    $def[3] .= "GPRINT:days:$item:\" %02.0lf days, \"\g ";
    $def[3] .= "GPRINT:hours:$item:\" %02.0lf hours, \"\g ";
    $def[3] .= "GPRINT:min:$item:\" %02.0lf min, \"\g ";
    $def[3] .= "GPRINT:sec:$item:\" %02.0lf sec\"\g ";
    $def[3] .= "COMMENT:\"\\n\" ";
}
?>
