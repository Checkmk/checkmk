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
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de


$opt[1] = "--vertical-label 'MB' -l 0  --title '$hostname / $servicedesc: Heap and Nonheap levels' ";
$def[1] = ""
         . "DEF:heap=$RRDFILE[1]:$DS[1]:MAX "
         . "DEF:nonheap=$RRDFILE[2]:$DS[1]:MAX "
         . "CDEF:min_nonheap=0,nonheap,- "
         . "CDEF:total=heap,nonheap,+ "

         . "AREA:heap#00c0ff:\"Heap\" ";
if ($MAX[1]) {
  $def[1] .= "LINE1:$MAX[1]#003077:\"Heap MAX\" ";
}
if ($CRIT[1]) {
  $def[1] .= "LINE1:$WARN[1]#a0ad00:\"Heap WARN\" "
           . "LINE1:$CRIT[1]#ad0000:\"Heap CRIT\" ";
}


$def[1] .= "AREA:min_nonheap#3430bf:\"Nonheap\" ";
if ($MAX[2]) {
  $def[1] .= "LINE1:-$MAX[2]#003233:\"Nonheap MAX \" ";
}
if ($CRIT[2]) {
  $def[1] .= "LINE1:-$WARN[2]#adfd30:\"Nonheap WARN\" "
           . "LINE1:-$CRIT[2]#ff0080:\"Nonheap CRIT\" ";
}


$def[1] .= "GPRINT:total:LAST:\"Total %.2lfMB last\" "
         . "GPRINT:total:AVERAGE:\"%.2lfMB avg\" "
         . "GPRINT:total:MAX:\"%.2lfMB max \" " . "";

?>
