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
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
