<?php

$desc = str_replace("_", " ", $servicedesc);

$opt[1] = "-X0 --vertical-label \"Response Time (ms)\"  --title \"$hostname / $desc\" ";


$def[1] = ""
 . "DEF:var1=$RRDFILE[1]:$DS[1]:MAX " 
 . "CDEF:ms=var1,1000,* "
 . "AREA:ms#20dd30:\"Response Time \" " 
 . "LINE1:ms#000000:\"\" " 
 . "GPRINT:ms:LAST:\"%3.3lg ms LAST \" " 
 . "GPRINT:ms:MAX:\"%3.3lg ms MAX \" " 
 . "GPRINT:ms:AVERAGE:\"%3.3lg ms AVERAGE \" " 
?>
