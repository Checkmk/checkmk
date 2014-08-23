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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

$title = str_replace("_", " ", $servicedesc);
$opt[1] = "--vertical-label 'ThreadRate' -l 0 --title \"ThreadRate of $title\" ";

$def[1] =  "DEF:var1=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "AREA:var1#F2F2F2:\"\" " ;
$def[1] .= "LINE1:var1#FF6600:\"ThreadRate \" " ;
$def[1] .= "GPRINT:var1:LAST:\"%3.2lf LAST \" ";
$def[1] .= "GPRINT:var1:MAX:\"%3.2lf MAX \" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"%3.2lf AVERAGE \" ";


$opt[2] = "--vertical-label \"ThreadCount\" -u102 -l0 --title \"Different ThreadCounts of $servicedesc\" ";
$def[2] = "DEF:var1=$RRDFILE[1]:$DS[2]:AVERAGE " ;
$def[2] .= "DEF:var2=$RRDFILE[1]:$DS[3]:AVERAGE " ;
$def[2] .= "DEF:var3=$RRDFILE[1]:$DS[4]:AVERAGE " ;
#
$def[2] .= "AREA:var1#FFFFFF:\"\" " ;
$def[2] .= "AREA:var2#FFFFFF:\"\" " ;
$def[2] .= "AREA:var3#FFFFFF:\"\" " ;
$def[2] .= "LINE1:var1#2B23FF:\"ThreadCount       \" " ;
$def[2] .= rrd::gprint("var1", array("LAST", "MAX", "AVERAGE"),"%3.0lf");
$def[2] .= "LINE1:var2#FF1420:\"DeamonThreadCount \" " ;
$def[2] .= rrd::gprint("var2", array("LAST", "MAX", "AVERAGE"),"%3.0lf");
$def[2] .= "LINE1:var3#0CD524:\"PeakThreadCount   \" " ;
$def[2] .= rrd::gprint("var3", array("LAST", "MAX", "AVERAGE"),"%3.0lf");

#TotalStartedThreadCount
$opt[3] = "--vertical-label \"TotalStartedThreadCount\" -l0 --title \"TotalStartedThreadCount of $title\" ";
#
$def[3] =  "DEF:var1=$RRDFILE[1]:$DS[5]:AVERAGE " ;
$def[3] .= "AREA:var1#F2F2F2:\"\" " ;
$def[3] .= "LINE1:var1#FF6600:\"TotalStartedThreadCount \" " ;
$def[3] .= "GPRINT:var1:LAST:\"%3.0lf current \" ";
?>

