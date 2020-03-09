<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
