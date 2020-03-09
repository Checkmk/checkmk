<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label 'Duration (sec)' -l0 --title \"Delivery Duration\" ";

$def[1] = "DEF:dur=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:dur#80f000:\"Duration (seconds)\" ";
$def[1] .= "LINE:dur#408000 ";
$def[1] .= "GPRINT:dur:LAST:\"%7.2lf %s LAST\" ";
$def[1] .= "GPRINT:dur:MAX:\"%7.2lf %s MAX\\n\" ";
if ($WARN[1])
    $def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning at $WARN[1] sec\" ";
if ($CRIT[1])
    $def[1] .= "HRULE:$CRIT[1]#FF0000:\"Critical at $CRIT[1] sec\" ";
?>
