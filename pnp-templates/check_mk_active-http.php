<?php
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
 . "AREA:size#cc66ff:\"Response Time \" " 
 . "LINE1:size#000000:\"\" " 
 . "GPRINT:size:LAST:\"%3.0lf Bytes LAST \" " 
 . "GPRINT:size:MAX:\"%3.0lf Bytes MAX \" " 
 . "GPRINT:size:AVERAGE:\"%3.0lf Bytes AVERAGE \" "
;

?>
