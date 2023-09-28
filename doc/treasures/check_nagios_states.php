<?php
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
