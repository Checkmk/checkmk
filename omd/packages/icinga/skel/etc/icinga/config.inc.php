<?php
// This file exists per site and configures site specific paths for
// Icinga' web pages


$cfg['cgi_config_file']='###ROOT###/etc/icinga/cgi.cfg';  // location of the CGI config file

$cfg['cgi_base_url']='/###SITE###/icinga/cgi-bin';


// FILE LOCATION DEFAULTS
$cfg['main_config_file']='###ROOT###/tmp/icinga/icinga.cfg';          // default location of the main Icinga config file
$cfg['status_file']='###ROOT###/tmp/icinga/status.dat';               // default location of Icinga status file
$cfg['state_retention_file']='###ROOT###/spool/icinga/retention.dat'; // default location of Icinga retention file



// utilities
require_once('###ROOT###/share/icinga/htdocs/includes/utils.inc.php');

?>
