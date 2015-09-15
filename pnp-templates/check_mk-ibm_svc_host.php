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

$opt[1] = '--vertical-label "Number of Hosts" --title "' . $this->MACRO['DISP_HOSTNAME'] . ' / ' . $this->MACRO['DISP_SERVICEDESC'] . ' per State" --lower=0';

$def[1] = ""
          . "DEF:active=$RRDFILE[1]:$DS[1]:MAX "
          . "DEF:inactive=$RRDFILE[2]:$DS[2]:MAX "
          . "DEF:degraded=$RRDFILE[3]:$DS[3]:MAX "
          . "DEF:offline=$RRDFILE[4]:$DS[4]:MAX "
          . "DEF:other=$RRDFILE[5]:$DS[5]:MAX "
          . "AREA:active#008000:\"Active             \" "
          . "GPRINT:active:AVERAGE:\"% 6.0lf Hosts avg\" "
          . "GPRINT:active:LAST:\"% 6.0lf Hosts last\\n\" "
          . "AREA:inactive#0000FF:\"Inactive           \":STACK "
          . "GPRINT:inactive:AVERAGE:\"% 6.0lf Hosts avg\" "
          . "GPRINT:inactive:LAST:\"% 6.0lf Hosts last\\n\" "
          . "AREA:degraded#F84:\"Degraded           \":STACK "
          . "GPRINT:degraded:AVERAGE:\"% 6.0lf Hosts avg\" "
          . "GPRINT:degraded:LAST:\"% 6.0lf Hosts last\\n\" "
          . "AREA:offline#FF0000:\"Offline            \":STACK "
          . "GPRINT:offline:AVERAGE:\"% 6.0lf Hosts avg\" "
          . "GPRINT:offline:LAST:\"% 6.0lf Hosts last\\n\" "
          . "AREA:other#000:\"Other              \":STACK "
          . "GPRINT:other:AVERAGE:\"% 6.0lf Hosts avg\" "
          . "GPRINT:other:LAST:\"% 6.0lf Hosts last\\n\" "
          . "";
