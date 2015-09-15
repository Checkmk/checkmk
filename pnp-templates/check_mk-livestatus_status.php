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

# Check Performance
$site_parts = explode("_", $servicedesc);
$site = $site_parts[1];

$opt[1] = "--vertical-label 'Checks per second' -X0 -l0  --title \"OMD site $site / Check performance\" ";
$ds_name[1] = "Check performance";

$def[1] = ""
          . "DEF:host_checks=$RRDFILE[1]:$DS[1]:MAX "
          . "DEF:service_checks=$RRDFILE[2]:$DS[2]:MAX "
          . "AREA:host_checks#842:\"Host checks             \" "
          . "GPRINT:host_checks:AVERAGE:\"% 6.1lf/s avg\" "
          . "GPRINT:host_checks:LAST:\"% 6.1lf/s last\\n\" "
          . "AREA:service_checks#f84:\"Service checks          \":STACK "
          . "GPRINT:service_checks:AVERAGE:\"% 6.1lf/s avg\" "
          . "GPRINT:service_checks:LAST:\"% 6.1lf/s last\\n\" "
          . "";


$opt[2] = "--vertical-label 'Events per second' -X0 -l0  --title \"OMD site $site / Livestatus performance\" ";
$ds_name[2] = "Livestatus performance";

$def[2] = ""
          . "DEF:connects=$RRDFILE[4]:$DS[4]:MAX "
          . "DEF:requests=$RRDFILE[5]:$DS[5]:MAX "
          . "AREA:requests#abc:\"Livestatus Requests     \" "
          . "GPRINT:requests:AVERAGE:\"% 6.1lf/s avg\" "
          . "GPRINT:requests:LAST:\"% 6.1lf/s last\\n\" "
          . "AREA:connects#678:\"Livestatus Connects     \" "
          . "GPRINT:connects:AVERAGE:\"% 6.1lf/s avg\" "
          . "GPRINT:connects:LAST:\"% 6.1lf/s last\\n\" "
          . "";

$opt[3] = "--vertical-label 'Requests per Connect' -X0 -l0  --title \"OMD site $site / Livestatus connection usage\" ";
$ds_name[3] = "Livestatus connection usage";

$def[3] = ""
          . "DEF:connects=$RRDFILE[4]:$DS[4]:MAX "
          . "DEF:requests=$RRDFILE[5]:$DS[5]:MAX "
          . "CDEF:rpcs=requests,connects,/ "
          . "AREA:rpcs#8a3:\"Requests per Connection\" "
          . "GPRINT:rpcs:AVERAGE:\"% 6.1lf/s avg\" "
          . "GPRINT:rpcs:LAST:\"% 6.1lf/s last\\n\" "
          . "";

