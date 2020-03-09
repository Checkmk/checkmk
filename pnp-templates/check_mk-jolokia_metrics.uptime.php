<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$title = str_replace("_", " ", $servicedesc);
$opt[1] = "--vertical-label 'Uptime (days)' -l0 --title \"$hostname / $title: Time since last reboot\" ";

$def[1] = "DEF:sec=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:uptime=sec,86400,/ ";
$def[1] .= "AREA:uptime#80f000:\"Uptime (days)\"\\n ";
$def[1] .= "LINE:uptime#408000 ";
$def[1] .= "GPRINT:uptime:LAST:\"%7.2lf %s LAST\"\\t ";
$def[1] .= "GPRINT:uptime:MAX:\"%7.2lf %s MAX\" ";
$def[1] .= "GPRINT:uptime:AVERAGE:\"%7.2lf %s AVG\" ";
?>
