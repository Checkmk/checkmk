<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# +------------------------------------------------------------------+
# | This file has been contributed and is copyrighted by:            |
# |                                                                  |
# | Joerg Linge 2009 <joerg.linge@pnp4nagios.org>     Copyright 2010 |
# +------------------------------------------------------------------+

$opt[1] = "--vertical-label '%'  -l0  --title \"LPAR CPU Usage\" ";

$def[1] =  "DEF:user=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:sys=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[1] .= "DEF:wait=$RRDFILE[3]:$DS[3]:AVERAGE " ;
$def[1] .= "DEF:idle=$RRDFILE[4]:$DS[4]:AVERAGE " ;

$def[1] .= "AREA:user#80ff40:\"user\\t\" " ;
$def[1] .= "GPRINT:user:LAST:\"%2.1lf %% last\" " ;
$def[1] .= "GPRINT:user:AVERAGE:\"%2.1lf MB avg\" " ;
$def[1] .= "GPRINT:user:MAX:\"%2.1lf MB max\\n\" ";

$def[1] .= "AREA:sys#008030:\"sys\\t\":STACK " ;
$def[1] .= "GPRINT:sys:LAST:\"%2.1lf %% last\" " ;
$def[1] .= "GPRINT:sys:AVERAGE:\"%2.1lf %% avg\" " ;
$def[1] .= "GPRINT:sys:MAX:\"%2.1lf %% max\\n\" " ;

$def[1] .= "AREA:wait#f00:\"wait\\t\":STACK " ;
$def[1] .= "GPRINT:wait:LAST:\"%2.1lf %% last\" " ;
$def[1] .= "GPRINT:wait:AVERAGE:\"%2.1lf %% avg\" " ;
$def[1] .= "GPRINT:wait:MAX:\"%2.1lf %% max\\n\" " ;

$def[1] .= "AREA:idle#00000020:\"idle\\t\":STACK " ;
$def[1] .= "GPRINT:idle:LAST:\"%2.1lf %% last\" " ;
$def[1] .= "GPRINT:idle:AVERAGE:\"%2.1lf %% avg\" " ;
$def[1] .= "GPRINT:idle:MAX:\"%2.1lf %% max\\n\" " ;

$opt[2] = "--vertical-label 'physc'  -l0  --title \"LPAR physical CPU usage\" ";

$def[2] =  "DEF:physc=$RRDFILE[5]:$DS[5]:AVERAGE " ;
$def[2] .= "AREA:physc#80ff40:\"physc\\t\" " ;
$def[2] .= "LINE1:physc#000: " ;
$def[2] .= "GPRINT:physc:LAST:\"%2.2lf last\" " ;
$def[2] .= "GPRINT:physc:AVERAGE:\"%2.2lf avg\" " ;
$def[2] .= "GPRINT:physc:MAX:\"%2.2lf max\\n\" ";
?>
