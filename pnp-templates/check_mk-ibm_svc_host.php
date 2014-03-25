<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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


#$opt[2] = "--vertical-label 'Events per second' -X0 -l0  --title \"OMD site $site / Livestatus performance\" ";
#$ds_name[2] = "Livestatus performance";
#
#$def[2] = ""
#          . "DEF:connects=$RRDFILE[4]:$DS[4]:MAX "
#          . "DEF:requests=$RRDFILE[5]:$DS[5]:MAX "
#          . "AREA:requests#abc:\"Livestatus Requests     \" "
#          . "GPRINT:requests:AVERAGE:\"% 6.1lf/s avg\" "
#          . "GPRINT:requests:LAST:\"% 6.1lf/s last\\n\" "
#          . "AREA:connects#678:\"Livestatus Connects     \" "
#          . "GPRINT:connects:AVERAGE:\"% 6.1lf/s avg\" "
#          . "GPRINT:connects:LAST:\"% 6.1lf/s last\\n\" "
#          . "";
#
#$opt[3] = "--vertical-label 'Requests per Connect' -X0 -l0  --title \"OMD site $site / Livestatus connection usage\" ";
#$ds_name[3] = "Livestatus connection usage";
#
#$def[3] = ""
#          . "DEF:connects=$RRDFILE[4]:$DS[4]:MAX "
#          . "DEF:requests=$RRDFILE[5]:$DS[5]:MAX "
#          . "CDEF:rpcs=requests,connects,/ "
#          . "AREA:rpcs#8a3:\"Requests per Connection\" "
#          . "GPRINT:rpcs:AVERAGE:\"% 6.1lf/s avg\" "
#          . "GPRINT:rpcs:LAST:\"% 6.1lf/s last\\n\" "
#          . "";
#
