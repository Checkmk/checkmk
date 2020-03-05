<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$desc = str_replace("_", " ", $servicedesc);
$opt[1] = "-X0 --vertical-label \"Response Time (ms)\"  --title \"$hostname / $desc\" ";

$def[1] = ""
 . "DEF:var1=$RRDFILE[1]:$DS[1]:MAX "
 . "CDEF:ms=var1,1000,* "
 . "AREA:ms#66ccff:\"Response Time \" "
 . "LINE1:ms#000000:\"\" "
 . "GPRINT:ms:LAST:\"%3.3lg ms LAST \" "
 . "GPRINT:ms:MAX:\"%3.3lg ms MAX \" "
 . "GPRINT:ms:AVERAGE:\"%3.3lg ms AVERAGE \" "
;

$opt[2] = "--vertical-label \"Size (Bytes)\" --title \"Size of response\" ";
$def[2] =  ""
  . "DEF:size=$RRDFILE[2]:$DS[2]:AVERAGE " ;
if ($WARN[2] != "")
    $def[2] .= "HRULE:$WARN[2]#FFFF00 ";
if ($CRIT[2] != "")
    $def[2] .= "HRULE:$CRIT[2]#FF0000 ";
$def[2] .= ""
 . "AREA:size#cc66ff:\"Size of response \" "
 . "LINE1:size#000000:\"\" "
 . "GPRINT:size:LAST:\"%3.0lf Bytes LAST \" "
 . "GPRINT:size:MAX:\"%3.0lf Bytes MAX \" "
 . "GPRINT:size:AVERAGE:\"%3.0lf Bytes AVERAGE \" "
;

for ( $idx = 3; $idx < count ( $RRDFILE ); $idx++ ) {
  preg_match ( "/(?<=_time_)[a-z]*(?=.rrd)/", $RRDFILE[$idx], $matches );
  if ( strtolower ( $matches[0] ) == "ssl" ) {
    $ds_name = strtoupper ( $matches[0] ) . " Time";
  }
  else {
    $ds_name = ucwords ( $matches[0] ) . " Time";
  }

  $opt[$idx] = "-X0 --vertical-label \"" . $ds_name . " (ms)\"  --title \"" . $ds_name . " (ms)\" ";
  $def[$idx] = ""
   . "DEF:var1=" . $RRDFILE[$idx] . ":" . $DS[$idx] . ":MAX "
   . "CDEF:ms=var1,1000,* "
   . "AREA:ms#66ccff:\"" . $ds_name . " \" "
   . "LINE1:ms#000000:\"\" "
   . "GPRINT:ms:LAST:\"%3.3lg ms LAST \" "
   . "GPRINT:ms:MAX:\"%3.3lg ms MAX \" "
   . "GPRINT:ms:AVERAGE:\"%3.3lg ms AVERAGE \" "
  ;
}


?>
