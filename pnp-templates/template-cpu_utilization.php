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
$def[1] .= "DEF:wait=$RRDFILE[3]:$DS[3]:AVERAGE " ;
$def[1] .= "CDEF:us=user,system,+ ";
$def[1] .= "CDEF:sum=us,wait,+ ";
$def[1] .= "CDEF:idle=100,sum,- ";

if ($TEMPLATE[1] == "check_mk-decru_cpu")
   $thirdname = "IRQs";
else
   $thirdname = "Wait";


$def[1] .= ""
        . "COMMENT:Average\:  "
        . "AREA:system#ff6000:\"System\" "
        . "GPRINT:system:AVERAGE:\"%4.1lf%%  \" "
        . "AREA:user#60f020:\"User\":STACK "
        . "GPRINT:user:AVERAGE:\"%4.1lf%%  \" "
        . "AREA:wait#00b0c0:\"$thirdname\":STACK "
        . "GPRINT:wait:AVERAGE:\"%4.1lf%%  \" "
        . "LINE:sum#004080:\"Total\" "
        . "GPRINT:sum:AVERAGE:\"%4.1lf%%  \\n\" "

        . "COMMENT:\"Last\:   \" "
        . "AREA:system#ff6000:\"System\" "
        . "GPRINT:system:LAST:\"%4.1lf%%  \" "
        . "AREA:user#60f020:\"User\":STACK "
        . "GPRINT:user:LAST:\"%4.1lf%%  \" "
        . "AREA:wait#00b0c0:\"$thirdname\":STACK "
        . "GPRINT:wait:LAST:\"%4.1lf%%  \" "
        . "LINE:sum#004080:\"Total\" "
        . "GPRINT:sum:LAST:\"%4.1lf%%  \\n\" "

        ."";

?>
