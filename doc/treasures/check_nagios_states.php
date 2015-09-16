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

$opt[1] = "-l 0 --vertical-label 'Number of Services' --title 'Number of services' ";

$def[1]  = "DEF:total=$RRDFILE[1]:$DS[1]:MAX "
          ."AREA:total#0000c0:\"Number of Services\" "
	  ."GPRINT:total:LAST:\"%4.0lf\\n\" "
          ."LINE:total#000000:\"\" ";

$opt[2] = "-l 0 --vertical-label 'Services' --title 'Problems' ";

$def[2]  = "" 
          ."DEF:warn=$RRDFILE[3]:$DS[3]:MAX "
          ."DEF:crit=$RRDFILE[4]:$DS[4]:MAX "
          ."DEF:unknown=$RRDFILE[5]:$DS[5]:MAX "
          ."DEF:pending=$RRDFILE[6]:$DS[6]:MAX "
          ."AREA:warn#ffff00:\"WARN   \" "
	  ."GPRINT:warn:LAST:\"%4.0lf\\n\" "
          ."AREA:unknown#ff8000:\"UKNOWN \":STACK "
	  ."GPRINT:unknown:LAST:\"%4.0lf\\n\" "
          ."AREA:crit#ff0000:\"CRIT   \":STACK "
	  ."GPRINT:crit:LAST:\"%4.0lf\\n\" "
          ."AREA:pending#808080:\"PENDING\":STACK "
	  ."GPRINT:pending:LAST:\"%4.0lf\\n\" "
;

?>
