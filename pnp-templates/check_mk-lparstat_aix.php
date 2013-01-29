<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
