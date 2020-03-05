<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$ds_name[1] = "Temperature";

$opt[1] = "--vertical-label 'Degrees C' --slope-mode -l0 -u 45 --title \"Temperature $hostname (Degrees C)\" -w 600";


$def[1] =  "DEF:load1=$RRDFILE[1]:$DS[1]:MAX ".
           "HRULE:$WARN[1]#ffe000:\"Warning at $WARN[1] C\" ".
           "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[1] C \\n\" ".
           "AREA:load1#40a018:\"Temperature (Degrees C)\" ".
           "GPRINT:load1:LAST:\"Cur\: %.0lf C \" ".
           "GPRINT:load1:AVERAGE:\"Avg\: %.0lf C \" ".
           "GPRINT:load1:MIN:\"Min\: %.0lf C \" ".
           "GPRINT:load1:MAX:\"Max\: %.0lf C \\n\" ".
           "";

?>
