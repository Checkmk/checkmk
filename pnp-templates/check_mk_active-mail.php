<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label 'Messages' -l0 --title \"$hostname / $servicedesc\" ";

$def[1] = "DEF:dur=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:dur#80f000:\"Messages\" ";
$def[1] .= "LINE:dur#408000 ";
$def[1] .= "GPRINT:dur:LAST:\"%7.2lf %s LAST\" ";
$def[1] .= "GPRINT:dur:MAX:\"%7.2lf %s MAX\\n\" ";
?>
