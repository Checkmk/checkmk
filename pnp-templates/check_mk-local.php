<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

$x = getcwd();

// try to find template matching a prefix of the service
// description first. Slashes are replaced by underscores.
$descr = str_replace("/", "_", $servicedesc);
$found = 0;
for ($i = strlen($descr); $i > 0; $i--)
{
   $tryname = 'templates/'.substr($descr, 0, $i) . ".php";
   if (file_exists($tryname) && include($tryname)) {
      $found = 1;
      break;
   }      
}

if (!$found) {
  $def[1] = "DEF:cnt=$RRDFILE[1]:$DS[1]:MAX "; 
  $def[1] .= "AREA:cnt#00ffc6:\"$servicedesc\" "; 
  $def[1] .= "LINE1:cnt#226600: "; 

  $upper = "";
  $lower = " -l 0";
  if ($WARN[1] != "") {
    $def[1] .= "HRULE:$WARN[1]#ffff00:\"Warning\" ";
  }
  if ($CRIT[1] != "") {
    $def[1] .= "HRULE:$CRIT[1]#ff0000:\"Critical\" ";
  }
  if ($MIN[1] != "") {
    $lower = " -l " . $MIN[1];
    $minimum = $MIN[1];
  }
  if ($MAX[1] != "") {
    $upper = " -u" . $MAX[1];
    $def[1] .= "HRULE:$MAX[1]#0000b0:\"Upper limit\" ";
  }

  $opt[1] = "$lower $upper --title '$hostname: $servicedesc' ";
  $def[1] .= "GPRINT:cnt:LAST:\"current\: %6.2lf\" ";
  $def[1] .= "GPRINT:cnt:MAX:\"max\: %6.2lf\" ";
  $def[1] .= "GPRINT:cnt:AVERAGE:\"avg\: %6.2lf\" ";
}


?>

