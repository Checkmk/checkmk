<?php
# +------------------------------------------------------------------+
# |                     _           _           _                    |
# |                  __| |_  ___ __| |__  _ __ | |__                 |
# |                 / _| ' \/ -_) _| / / | '  \| / /                 |
# |                 \__|_||_\___\__|_\_\_|_|_|_|_\_\                 |
# |                                   |___|                          |
# |              _   _   __  _         _        _ ____               |
# |             / | / | /  \| |__  ___| |_ __ _/ |__  |              |
# |             | |_| || () | '_ \/ -_)  _/ _` | | / /               |
# |             |_(_)_(_)__/|_.__/\___|\__\__,_|_|/_/                |
# |                                            check_mk 1.1.0beta17  |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
# 
# This file is part of check_mk 1.1.0beta17.
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

$subtype = substr($servicedesc, 7);
if ($subtype == "pgmajfault") {
  $title = "Major Page Faults";
  $vertical = "faults / sec";
  $format = "%5.1lf/s";
  $upto = "500";
  $color = "20ff80";
  $line = "10a040";
}
else if ($subtype == "ctxt") {
  $title = "Context Switches";
  $vertical = "switches / sec";
  $format = "%5.1lf/s";
  $upto = "50000";
  $color = "80ff20";
  $line = "40a010";
}
else if ($subtype == "processes") {
  $title = "Process creation";
  $vertical = "new processes / sec";
  $format = "%5.1lf/s";
  $upto = "100";
  $color = "ff8020";
  $line = "a04010";
}
else {
  $title = "Kernel counter $subtype";
  $vertical = "per sec";
  $format = "%3.0lf";
  $upto = "100";
  $color = "ffff20";
  $line = "90a010";
}

$opt[1] = " --vertical-label \"$vertical\" -X0 -l 0 -u $upto --title \"$title\" ";

$def[1] = "DEF:var1=$rrdfile:$DS[1]:MAX ";
$def[1] .= "AREA:var1#$color:\"$title\:\" ";
$def[1] .= "LINE1:var1#$line:\"\" ";
$def[1] .= "GPRINT:var1:LAST:\"Current\: $format\" ";
if ($WARN[1])
	$lf = "\\n";
else
	$lf = "";
	
$def[1] .= "GPRINT:var1:MAX:\"Maximum\: $format$lf\" ";
if ($WARN[1]) {
 $def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning\: $WARN[1]C\" ";
 $def[1] .= "HRULE:$CRIT[1]#FF0000:\"Critical\: $CRIT[1]C\" ";
}
?>
