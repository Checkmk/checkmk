<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

$title = str_replace("_", " ", $servicedesc);


$opt[1] = "--vertical-label 'GB' -l0 --title \"$title\" ";
#
$def[1] =  "DEF:current=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:used=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "DEF:max=$RRDFILE[3]:$DS[3]:MAX " ;
$def[1] .= "CDEF:current_gb=current,1073741824.0,/ ";
$def[1] .= "CDEF:max_gb=max,1073741824.0,/ ";
$def[1] .= "CDEF:used_gb=used,1073741824.0,/ ";

$def[1] .= "AREA:max_gb#80c0ff:\"Maximum size\" " ;
$def[1] .= "LINE:max_gb#6080c0:\"\" " ;
$def[1] .= "GPRINT:max_gb:LAST:\"%2.2lfGB\" ";
$def[1] .= "AREA:current_gb#00ff80:\"Current size\" " ;
$def[1] .= "LINE:current_gb#008040:\"\" " ;
$def[1] .= "GPRINT:current_gb:LAST:\"%2.2lfGB\" ";
$def[1] .= "AREA:used_gb#f0b000:\"Used by user data\" " ;
$def[1] .= "LINE:used_gb#806000:\"\" " ;
$def[1] .= "GPRINT:used_gb:LAST:\"%2.2lfGB\" ";

?>
