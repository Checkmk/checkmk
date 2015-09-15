<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

$opt[1] = "--vertical-label 'CPU utilization %' -l0  -u 100 --title \"CPU Utilization for $hostname\" ";
#
$def[1] =  "DEF:user=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:system=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[1] .= "DEF:idle=$RRDFILE[3]:$DS[3]:AVERAGE " ;
$def[1] .= "DEF:nice=$RRDFILE[4]:$DS[4]:AVERAGE " ;
$def[1] .= "CDEF:sum=user,system,+,nice,+ ";

$def[1] .= "AREA:user#60f020:\"User\" " ;
$def[1] .= "GPRINT:user:LAST:\"%2.1lf%%\" " ;

$def[1] .= "AREA:system#ff6000:\"System\":STACK " ;
$def[1] .= "GPRINT:system:LAST:\"%2.1lf%%\" " ;

$def[1] .= "AREA:nice#00d080:\"Nice\":STACK " ;
$def[1] .= "GPRINT:nice:LAST:\"%2.1lf%%\" " ;

$def[1] .= "LINE:idle#ffffff:\"Idle\":STACK " ;
$def[1] .= "GPRINT:idle:LAST:\"%2.1lf%%\" " ;

$def[1] .= "LINE:sum#004080:\"Utilization\" " ;

?>
