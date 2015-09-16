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

$license = substr($servicedesc, 16);
$opt[1] = "--vertical-label Licenses -l 0 -u $MAX[1] --title 'Used Citrix Licenses - $license'";

$def[1] = ""
          . "DEF:used=$RRDFILE[1]:$DS[1]:MAX "
          . "AREA:used#60d070:\"Used Licenses: \" "
          . "GPRINT:used:LAST:\"last\\: % 6.0lf\" "
          . "GPRINT:used:MAX:\"maximum\\: % 6.0lf\" "
          . "GPRINT:used:AVERAGE:\"average\\:% 6.0lf\\n\" "
          . "HRULE:$MAX[1]#000000:\"Installed Licences\" "
          . "LINE:used#008000 "
          . "";
