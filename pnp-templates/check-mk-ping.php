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

$ds_name[1] = "Round Trip Averages";
$opt[1] = "--vertical-label \"RTA (ms)\" --title \"Ping times for $hostname\" ";
$def[1] =  "DEF:var1=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:var2=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "VDEF:maxrta=var1,MAXIMUM " ;
$def[1] .= "CDEF:loss1=var2,100,/,maxrta,* " ;
$def[1] .= "CDEF:sp1=var1,100,/,12,* " ;
$def[1] .= "CDEF:sp2=var1,100,/,30,* " ;
$def[1] .= "CDEF:sp3=var1,100,/,50,* " ;
$def[1] .= "CDEF:sp4=var1,100,/,70,* " ;
$def[1] .= "CDEF:loss2=loss1,100,/,80,* " ;
$def[1] .= "CDEF:loss3=loss1,100,/,60,* " ;
$def[1] .= "CDEF:loss4=loss1,100,/,40,* " ;
$def[1] .= "CDEF:loss5=loss1,100,/,20,* " ;

$def[1] .= "AREA:var1#00FF5C:\"Round Trip Times \" " ;
$def[1] .= "AREA:sp4#00FF7C: " ;
$def[1] .= "AREA:sp3#00FF9C: " ;
$def[1] .= "AREA:sp2#00FFBC: " ;
$def[1] .= "AREA:sp1#00FFDC: " ;
$def[1] .= "LINE1:var1#000000:\"\" " ;
$def[1] .= "GPRINT:var1:LAST:\"%6.2lf $UNIT[1] last \" " ;
$def[1] .= "GPRINT:var1:MAX:\"%6.2lf $UNIT[1] max \" " ;
$def[1] .= "GPRINT:var1:AVERAGE:\"%6.2lf $UNIT[1] avg \\n\" " ;

$def[1] .= "AREA:loss1#F20:\"Packet Loss        \" ";
$def[1] .= "AREA:loss2#F40 ";
$def[1] .= "AREA:loss3#F60 ";
$def[1] .= "AREA:loss4#F80 ";
$def[1] .= "AREA:loss5#FA0 ";

$def[1] .= "GPRINT:var2:MAX:\"%3.0lf $UNIT[2] max \\n\" " ;

?>
