<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

$opt[1] = "--vertical-label 'Bytes' -l0 --title \"$title\" ";
#
$def[1] =  "DEF:size=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:unallocated=$RRDFILE[2]:$DS[1]:MAX " ;
$def[1] .= "DEF:data=$RRDFILE[4]:$DS[1]:MAX " ;
$def[1] .= "DEF:indexes=$RRDFILE[5]:$DS[1]:MAX " ;
$def[1] .= "DEF:unused=$RRDFILE[6]:$DS[1]:MAX " ;

$def[1] .= "AREA:size#f7f7f7:\"Size    \" " ;
$def[1] .= "GPRINT:size:LAST:\"%4.2lf%sB\" ";

$def[1] .= "AREA:data#80c0ff:\"Data       \" " ;
$def[1] .= "LINE:data#6080c0:\"\" " ;
$def[1] .= "GPRINT:data:LAST:\"%4.2lf%sB\" ";

$def[1] .= "AREA:indexes#00ff80:\"Indexes\":STACK " ;
$def[1] .= "GPRINT:indexes:LAST:\"%4.2lf%sB\\n\" ";

$def[1] .= "AREA:unused#f0b000:\"Unused\":STACK " ;
$def[1] .= "GPRINT:unused:LAST:\"%4.2lf%sB\" ";

$def[1] .= "AREA:unallocated#dfdfdf:\"Unallocated\":STACK " ;
$def[1] .= "GPRINT:unallocated:LAST:\"%4.2lf%sB\\n\" ";


?>
