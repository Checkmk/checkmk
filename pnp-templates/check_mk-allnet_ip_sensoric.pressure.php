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

$opt[1] = "--vertical-label \"bars\" --title \"$hostname / $servicedesc\" ";

$def[1] = "DEF:var1=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "LINE2:var1#2080ff:\"Pressure\:\" ";
$def[1] .= "GPRINT:var1:LAST:\"%0.5lf bars\\n\" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"(Avg\: %0.5lf bars,\" ";
$def[1] .= "GPRINT:var1:MIN:\"Min\: %0.5lf bars,\" ";
$def[1] .= "GPRINT:var1:MAX:\"Max\: %0.5lf bars)\" ";
?>
