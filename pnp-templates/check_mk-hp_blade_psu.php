<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

#
# PNP4Nagios template for check_mk hp_blade_psu check
# http://mathias-kettner.de/ FIXME: Link to checks man page
#
# Author: Lars Michelsen <lm@mathias-kettner.de>
#

function getAllPsuFiles($path) {
  $files = array();
  if($h = opendir($path)) {
		while(($file = readdir($h)) !== false) {
      if(preg_match('/^PSU_[0-9]+\.rrd$/', $file, $aRet))
        $files[] = $aRet[0];
    }
		natcasesort($files);
    closedir($h);
  }
  return $files;
}

$colors = array("008CFF", "6FBEFF", "2F7EBF", "00589F");

$path  = dirname($RRDFILE[1]);
$files = getAllPsuFiles($path);

$opt[0] = "-l 0 --vertical-label \"Watt\" --title \"HP Blade Enclosure - PSU Power Usage\" ";
$def[0] = '';

$i = 0;
foreach($files AS $file) {
  $color = $colors[$i % 4];
  $name  = str_replace('_', ' ', str_replace('.rrd', '', $file));

  $def[0] .= "DEF:var$i=$path/$file:$DS[1]:AVERAGE " ;
  if($i == 0)
	  $def[0] .= "AREA:var$i#$color:\"$name\" " ;
  else
	  $def[0] .= "AREA:var$i#$color:\"$name\":STACK " ;
  $def[0] .= "GPRINT:var$i:LAST:\"%6.0lfW last \" ";
  $def[0] .= "GPRINT:var$i:MAX:\"%6.0lfW max \" ";
  $def[0] .= "GPRINT:var$i:AVERAGE:\"%6.2lfW  avg \\n\" ";
  $i++;
}
?>
