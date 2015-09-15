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

$opt[1] = '--vertical-label "%" --title "' . $this->MACRO['DISP_HOSTNAME'] . ' / ' . $this->MACRO['DISP_SERVICEDESC'] . '" --lower=0 -u 100';

$def[1] = ""
          . "DEF:write_cache_pc=$RRDFILE[1]:$DS[1]:MAX "
          . "DEF:total_cache_pc=$RRDFILE[2]:$DS[2]:MAX "
          . "LINE1:write_cache_pc#008000:\"Write Cache Usage      \" "
          . "GPRINT:write_cache_pc:AVERAGE:\"% 6.0lf%% avg\" "
          . "GPRINT:write_cache_pc:LAST:\"% 6.0lf%% last\\n\" "
          . "LINE1:total_cache_pc#0000FF:\"Total Cache Usage      \" "
          . "GPRINT:total_cache_pc:AVERAGE:\"% 6.0lf%% avg\" "
          . "GPRINT:total_cache_pc:LAST:\"% 6.0lf%% last\\n\" "
          . "";
