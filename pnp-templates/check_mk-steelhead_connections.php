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

# active=20;;;; established=8;;;; halfOpened=3;;;; halfClosed=4;;;; passthrough=35;;;;
$opt[1] = "--vertical-label 'Connections' -l0  --title \"Current connections on $hostname\" ";

$def[1] =  "DEF:active=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:est=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "DEF:open=$RRDFILE[3]:$DS[3]:MAX " ;
$def[1] .= "DEF:close=$RRDFILE[4]:$DS[4]:MAX " ;
$def[1] .= "DEF:pass=$RRDFILE[5]:$DS[5]:MAX " ;
$def[1] .= "CDEF:opt=active,est,open,close,+,+,+ ";
$def[1] .= "CDEF:total=opt,pass,+ ";

$def[1] .= "AREA:active#30c040:\"Active    \" " ;
$def[1] .= "GPRINT:active:LAST:\"%3.0lf\" " ;

$def[1] .= "AREA:est#40ff80:\"Established\":STACK " ;
$def[1] .= "GPRINT:est:LAST:\"%3.0lf\" " ;

$def[1] .= "AREA:open#0080c0:\"Half opened\":STACK " ;
$def[1] .= "GPRINT:open:LAST:\"%2.0lf\" " ;

$def[1] .= "AREA:close#00a0f0:\"Half closed\":STACK " ;
$def[1] .= "GPRINT:close:LAST:\"%2.0lf\\n\" " ;


$def[1] .= "LINE:total#ff3030:\"Total     \" " ;
$def[1] .= "GPRINT:total:LAST:\"%3.0lf\" " ;

$def[1] .= "LINE:opt#008000:\"Optimized  \" " ;
$def[1] .= "GPRINT:opt:LAST:\"%3.0lf\" " ;

$def[1] .= "AREA:pass#ffd0d0:\"Passthrough\":STACK " ;
$def[1] .= "GPRINT:pass:LAST:\"%3.0lf\"\\n " ;



?>
