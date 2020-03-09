<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

setlocale(LC_ALL, "POSIX");

# RRDtool Options
#$servicedes=$NAGIOS_SERVICEDESC

$fsname = str_replace("_", "/", substr($servicedesc, 3));
$fstitle = $fsname;

# Hack for windows: replace C// with C:\
if (strlen($fsname) == 3 && substr($fsname, 1, 2) == '//') {
    $fsname = $fsname[0] . "\:\\\\";
    $fstitle = $fsname[0] . ":\\";
}

$mega  = 1024.0 * 1024.0;
$giga  = 1024.0 * 1024.0 * 1024.0;
$sizegb = sprintf("%.1f", $MAX[1] / $giga);
$maxgb  = $MAX[1]  / $giga;
$warngb = $WARN[1] / $giga;
$critgb = $CRIT[1] / $giga;
$warngbtxt = sprintf("%.1f", $warngb);
$critgbtxt = sprintf("%.1f", $critgb);

$opt[1] = "--vertical-label GB -l 0 -u $maxgb -b 1024 --title '$hostname: Filesystem $fstitle ($sizegb GB)' ";

# First graph show current filesystem usage
$def[1] = "DEF:used_bytes=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:var1=used_bytes,$giga,/ ";
$def[1] .= "AREA:var1#00ffc6:\"used space on $fsname\\n\" ";
$def[1] .= "LINE1:var1#226600: ";
$def[1] .= "HRULE:$maxgb#003300:\"Size ($sizegb GB) \" ";
$def[1] .= "HRULE:$warngb#ffff00:\"Warning at $warngbtxt GB \" ";
$def[1] .= "HRULE:$critgb#ff0000:\"Critical at $critgbtxt GB \\n\" ";
$def[1] .= "GPRINT:var1:LAST:\"current\: %6.2lf GB\" ";
$def[1] .= "GPRINT:var1:MAX:\"max\: %6.2lf GB \" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"avg\: %6.2lf GB\" ";

?>
