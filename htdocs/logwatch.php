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

$vardir="/var/lib/check_mk";

$host = str_replace("/", "_", $_GET["host"]);
$path=$vardir . "/logwatch/$host";

# Handle Cookie
if ($_GET["HIDECONTEXT"] == "yes") {
  setcookie("HIDECONTEXT", "yes", 2147483640);
  $hide_context = true;
}
else if ($_GET["HIDECONTEXT"] == "no") {
  setcookie("HIDECONTEXT", "no", 2147483640);
  $hide_context = false;
}
else {
  $chk = $_COOKIE["HIDECONTEXT"];
  $hide_context = ($chk == "yes");
}

# $file is the name of the logfile-file unter $vardir/logwatch
# $filename is the original name of then logfile on the target host
$file = $_GET["file"];
if (substr($file, 0, 4) == "LOG ")
  $file = substr($file, 4);

// Hack: '+' signs in URLs are replaced with spaces by the web server
// (which is correct). Unfortunately the URLs check_mk creates do not
// correctly quote + signs. We should fix this in the Nagios config
// generation of check_mk rather then here!
// $file = str_replace(" ", "+", $file);
$file = str_replace("/", "\\", $file);
$file = str_replace("\\\\", "\\", $file); # due to PHP magic quotes
$filenice = str_replace("\\","/", $file);

$naglink = "<a href=\"cgi-bin/status.cgi?host=$host\">Back to this host in Nagios</a><br>\n";

if ($_GET["ACK"] == "1") {
   if (@unlink($path . "/" . $file)) {
      echo "<p><b>Errormessages from $filenice acknowledged and deleted.</b><br>\n";
   }
   else {
      echo "<P class=syserror><b>Cannot delete logfile.</b><br> Please check permissions ".
	"of <tt>$path</tt> and make sure that the webserver process ".
	"has write access to that directory! If you set the variable <tt>logwatch_groupid</tt> ".
	"in <tt>main.mk</tt> to a group id (numerical), then the logfile subdirectories ".
	"under <tt>$vardir/logwatch</tt> will be created with write ".
	"access for that group. Both the webserver and the Nagios process must ".
	"be members of that group.\n</p>";
    }
}


echo "<html><head><title>Logmessages of host $host</title>
<link rel=\"stylesheet\" type=\"text/css\" href=\"logwatch.css\">
</style>
</head><body>\n";

function title($title)
{
  echo "<table width=\"100%\"><tr><td valign=top>".
    "<h1>$title</h1>".
    "</td><td valign=top align=right>".
    "<a href=\"http://mathias-kettner.de/check_mk\">".
    "<img border=0 src=\"check_mk.gif\"></a>".
    "</td></tr></table>\n";
}

if (!$file) {
  /* show list of all logfiles */
  title("Logfiles of host '$host'");
  echo $naglink;
  echo "<p>";
  if ($handle = opendir($path))
  {   
    while (false !== ($file = readdir($handle))) {
        if ($file != "." and $file != "..") {
         $filenice = str_replace("\\","/", $file);
         $fileurl = urlencode($file);
         echo "<a href=\"logwatch.php?host=$host&file=$fileurl\"><b>$filenice</b></a><br>\n"; 
        }
    }
  }
  else
      echo "No unacknowledged error messages (dir: $path)\n";
}
/* show one specific logfile */



else {
  title("Host '$host'");
  echo $naglink;
  echo "<a href=\"logwatch.php?host=$host\">All Logmessages of this host</a><br>\n";
  
  if (file_exists($path . "/" . $file)) {
    echo "<h2>$filenice</h2>\n";
    $f = fopen($path . "/" . $file, "r");
    if ($f) {
      $chunk_open = 0;
      while (!feof($f)) {
	$line = fgets($f);
	if (trim($line) == "") continue;

	if (substr($line, 0, 3) == "<<<") {
	  $parts = explode(" ", substr($line, 3, strlen($line)-7));
	  $date = $parts[0];
	  $time = $parts[1];
	  $level = $parts[2];
	  $selfuri = $_SERVER["REQUEST_URI"];
	  if ($hide_context)
	    $contextlink = "<a href=\"$selfuri&HIDECONTEXT=no\">Show context</a>";
	  else
	    $contextlink = "<a href=\"$selfuri&HIDECONTEXT=yes\">Hide context</a>";
	  if ($chunk_open)
	    echo "</div>\n";
	  echo "<div class=chunk>\n".
	    "<table border=0 cellspacing=0 cellpadding=0 class=section><tr>".
	    "<td class=$level>$level</td>".
	    "<td class=date>$date&nbsp; $time</td>".
	    "<td class=button>$contextlink</td>".
	    "</tr></table>";
	  $chunk_open = 1;
	}
	else {
	  $text = substr($line, 2);
	  if ($line[0] == "W")
	    $class = "WARN";
	  else if ($line[0] == "C")
	    $class = "CRIT";
          else {
	    if ($hide_context)
	      continue;
	    $class = "context";
	  }
          
	  echo "<pre class=$class>" . htmlspecialchars(substr($line, 2)) . "</pre>\n";
	}
      }
      if ($chunk_open)
	echo "</div>\n";
      $fileurl=urlencode($file);
      echo "<p><br><a class=ack href=\"logwatch.php?host=$host&file=$fileurl&ACK=1\">Acknowledge and delete messages!</a>";
    }
    else {
      echo "<P class=syserror><b>Could not open $path/$file for reading.</b><br>".
	"Please make sure that your webserver process has read access to that file.</p>";
    }
    
  }
  else {
     echo "<p>No error messages in logfile $filenice.<br>\n";
  }
}

echo "</body></html>\n";

?>
