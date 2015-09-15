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

$servicename_parts = explode("_", $servicedesc);
$oracle_sid = $servicename_parts[1];

$opt[1] = "--vertical-label 'apply Lag (s)' -l0 --title \"Dataguard Stats of $oracle_sid\" ";

$def[1] = "DEF:sec=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:apply_lag=sec,1,/ ";
$def[1] .= "AREA:apply_lag#80f000:\"Apply Lag (s)\" ";
$def[1] .= "LINE:apply_lag#408000 ";
$def[1] .= "GPRINT:apply_lag:LAST:\"%7.2lf %s LAST\" ";
$def[1] .= "GPRINT:apply_lag:MAX:\"%7.2lf %s MAX\" ";
?>
