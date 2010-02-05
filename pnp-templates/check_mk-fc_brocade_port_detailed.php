<?php

# Quellen:
#  1: txbytes
#  2: rxbytes
#  3: crcerrors
#  4: encout
#  5: c3discards

$ds_name[1] = 'Traffic';
$opt[1]  = "--vertical-label \"MB/sec\" -X0 -b 1024 --title \"Traffic for $hostname / $servicedesc\" ";
$def[1]  = "DEF:txwords=$rrdfile:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:rxwords=$rrdfile:$DS[2]:AVERAGE " ;
$def[1] .= "CDEF:txbytes=txwords,4,* " ;
$def[1] .= "CDEF:rxbytes=rxwords,4,* " ;
$def[1] .= "CDEF:rxMbytes=rxbytes,1048576.0,/ " ;
$def[1] .= "CDEF:txMbytes=txbytes,1048576.0,/ " ;
$def[1] .= "CDEF:rxMbytesDraw=rxMbytes,-1,* " ;
$def[1] .= "AREA:txMbytes#60a020:\"in \" " ;
$def[1] .= "GPRINT:txMbytes:LAST:\"%.2lf MB/s last\" " ;
$def[1] .= "GPRINT:txMbytes:AVERAGE:\"%.2lf MB/s avg\" " ;
$def[1] .= "GPRINT:txMbytes:MAX:\"%.2lf MB/s max\\n\" " ;
$def[1] .= "AREA:rxMbytesDraw#2060a0:\"out\" " ;
$def[1] .= "GPRINT:rxMbytes:LAST:\"%.2lf MB/s last\" " ;
$def[1] .= "GPRINT:rxMbytes:AVERAGE:\"%.2lf MB/s avg\" " ;
$def[1] .= "GPRINT:rxMbytes:MAX:\"%.2lf MB/s max\\n\" " ;

$ds_name[2] = 'Error counter';
$opt[2]  = "--vertical-label \"Error counter\" --title \"Problems on $hostname / $servicedesc\" ";
$def[2]  = "DEF:crcerrors=$rrdfile:$DS[3]:AVERAGE " ;
$def[2] .= "DEF:encout=$rrdfile:$DS[4]:AVERAGE " ;
$def[2] .= "DEF:c3discards=$rrdfile:$DS[5]:AVERAGE " ;
$def[2] .= "LINE1:crcerrors#ff0000:\"CRC Errors      \" " ;
$def[2] .= "GPRINT:crcerrors:LAST:\"%.0lf\\n\" " ;
$def[2] .= "LINE1:encout#60a020:\"ENC-Out         \" " ;
$def[2] .= "GPRINT:encout:LAST:\"%.0lf\\n\" " ;
$def[2] .= "LINE1:c3discards#2060a0:\"Class 3 Discards\" " ;
$def[2] .= "GPRINT:c3discards:LAST:\"%.0lf\\n\" " ;
?>
