<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label \"%\"  -l 0 --title \"$hostname / $servicedesc\" ";

$def[1] = "DEF:var1=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:var1#808080:\"Smoke\:\" ";
$def[1] .= "GPRINT:var1:LAST:\"%0.6lf%%\" ";
$def[1] .= "LINE1:var1#000080:\"\" ";
$def[1] .= "GPRINT:var1:MAX:\"(Max\: %0.6lf%%,\" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"Avg\: %0.6lf%%)\" ";
?>
