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



# cut TSM part from service description
$item = substr($servicedesc, 16);
# if ___ is in the item, then we have info on the TSM farm and the Poolname
# split it. otherwise, keep the item name unchanged.
$parts    = explode("___", $item);
$info = (isset($parts[1])) ? $parts[1] . " (".$parts[0].")" : $item;


$opt[1] = "-l0 --vertical-label \"Tapes\" --title \"Occupancy of $info\" ";


$def[1]  = "DEF:tapes=$RRDFILE[1]:$DS[1]:MAX ".
           "DEF:free=$RRDFILE[2]:$DS[1]:MAX ".
           "DEF:util=$RRDFILE[3]:$DS[1]:MAX ".
           "AREA:tapes#cd853f:\"Tapes in Pool   \" ".
           "AREA:free#a000ff:\"Free Tapes   \" ".
           "LINE3:util#5f1010:\"Utilization   \" ".
           "";

?>
