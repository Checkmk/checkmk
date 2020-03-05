<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Modified by: Chris Bowlby <cbowlby@tenthpowertech.com>
#
$ds_name[1] = "CPU Utilization Load Averages";

$opt[1] = "--vertical-label 'CPU utilization (%)' --slope-mode -l0 -u 100 --title \"CPU Utilization $hostname\" -w 600";


$def[1] =  "DEF:load1=$RRDFILE[1]:$DS[1]:MAX ".
	   "DEF:load2=$RRDFILE[2]:$DS[2]:MAX ".
	   "DEF:load3=$RRDFILE[3]:$DS[3]:MAX ".
	   "HRULE:$WARN[1]#ffe000:\"Warning at $WARN[1]%\" ".
	   "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[1]% \\n\" ".
	   "AREA:load1#40a018:\"CPU Load (1s)\" ".
	   "GPRINT:load1:LAST:\"Cur\: %.0lf %s$UNIT[1] \" ".
	   "GPRINT:load1:AVERAGE:\"Avg\: %.0lf %s$UNIT[1] \" ".
	   "GPRINT:load1:MIN:\"Min\: %.0lf %s$UNIT[1] \" ".
	   "GPRINT:load1:MAX:\"Max\: %.0lf %s$UNIT[1] \\n\" ".
	   "LINE:load2#0011FF:\"CPU Load (1m)\" ".
	   "GPRINT:load2:LAST:\"Cur\: %.0lf %s$UNIT[2] \" ".
	   "GPRINT:load2:AVERAGE:\"Avg\: %.0lf %s$UNIT[2] \" ".
	   "GPRINT:load2:MIN:\"Min\: %.0lf %s$UNIT[2] \" ".
	   "GPRINT:load2:MAX:\"Max\: %.0lf %s$UNIT[2] \\n\" ".
	   "LINE:load3#00AAFF:\"CPU Load (5m)\" ".
	   "GPRINT:load3:LAST:\"Cur\: %.0lf %s$UNIT[3] \" ".
	   "GPRINT:load3:AVERAGE:\"Avg\: %.0lf %s$UNIT[3] \" ".
	   "GPRINT:load3:MIN:\"Min\: %.0lf %s$UNIT[3] \" ".
	   "GPRINT:load3:MAX:\"Max\: %.0lf %s$UNIT[3] \\n\" ".
	   "";

?>
