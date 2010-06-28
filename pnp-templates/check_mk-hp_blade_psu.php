<?php
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
  $color = $colors[$i];
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
