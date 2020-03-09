<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

// try to find template matching a prefix of the service
// description first. Slashes are replaced by underscores.
$template_dirs = array('templates');
if (isset($this->config->conf['template_dirs'])) {
	$template_dirs = $this->config->conf['template_dirs'];
}
$descr = str_replace("/", "_", $servicedesc);
foreach ($template_dirs as $template_dir) {
  $found = 0;
  for ($i = strlen($descr); $i > 0; $i--)
  {
     $tryname = $template_dir . '/' . substr($descr, 0, $i) . '.php';
     if (file_exists($tryname) && include($tryname)) {
        $found = 1;
        break;
     }
  }
  if ($found) {
     break;
  }
}

# Use another color for each graph. After eight graphs colors wrap around.
$area_colors = array( "beff5f", "5fffef", "5faaff", "cc5fff", "ff5fe2", "ff5f6c", "ff975f", "ffec5f");
$line_colors = array( "5f7a2f", "2f8077", "2f5580", "662f80", "802f71", "802f36", "804b2f", "80762f");

if (!$found) {
    foreach ($RRDFILE as $i => $RRD) {
      $ii = $i % 8;
      $name = $NAME[$i];
      $def[$i] = "DEF:cnt=$RRDFILE[$i]:$DS[$i]:MAX ";
      $def[$i] .= "AREA:cnt#$area_colors[$ii]:\"$name\" ";
      $def[$i] .= "LINE1:cnt#$line_colors[$ii]: ";

      $upper = "";
      $lower = " -l 0";
      if ($WARN[$i] != "") {
        $def[$i] .= "HRULE:$WARN[$i]#ffff00:\"Warning\" ";
      }
      if ($CRIT[$i] != "") {
        $def[$i] .= "HRULE:$CRIT[$i]#ff0000:\"Critical\" ";
      }
      if ($MIN[$i] != "") {
        $lower = " -l " . $MIN[$i];
        $minimum = $MIN[$i];
      }
      if ($MAX[$i] != "") {
        $upper = " -u" . $MAX[$i];
        $def[$i] .= "HRULE:$MAX[$i]#0000b0:\"Upper limit\" ";
      }

      $opt[$i] = "$lower $upper --title '$hostname: $servicedesc - $name' ";
      $def[$i] .= "GPRINT:cnt:LAST:\"current\: %6.2lf\" ";
      $def[$i] .= "GPRINT:cnt:MAX:\"max\: %6.2lf\" ";
      $def[$i] .= "GPRINT:cnt:AVERAGE:\"avg\: %6.2lf\" ";
    }
}

?>
