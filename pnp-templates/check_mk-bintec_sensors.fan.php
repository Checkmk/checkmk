<?php
#
# Copyright (c) 2006-2010 Joerg Linge (http://www.pnp4nagios.org)
# Default Template used if no other template is found.
# Don`t delete this file ! 
#
# Define some colors ..
#
$_WARNRULE = '#FFFF00';
$_CRITRULE = '#FF0000';
$_AREA     = '#256aef';
$_LINE     = '#000000';
#
# Initial Logic ...
#

foreach ($this->DS as $KEY=>$VAL) {

	$maximum  = "";
	$minimum  = "";
	$critical = "";
	$crit_min = "";
	$crit_max = "";
	$warning  = "";
	$warn_max = "";
	$warn_min = "";
	$vlabel   = " ";
	$lower    = "";
	$upper    = "";
	
	if ($VAL['WARN'] != "" && is_numeric($VAL['WARN']) ){
		$warning = $VAL['WARN'];
	}
	if ($VAL['WARN_MAX'] != "" && is_numeric($VAL['WARN_MAX']) ) {
		$warn_max = $VAL['WARN_MAX'];
	}
	if ( $VAL['WARN_MIN'] != "" && is_numeric($VAL['WARN_MIN']) ) {
		$warn_min = $VAL['WARN_MIN'];
	}
	if ( $VAL['CRIT'] != "" && is_numeric($VAL['CRIT']) ) {
		$critical = $VAL['CRIT'];
	}
	if ( $VAL['CRIT_MAX'] != "" && is_numeric($VAL['CRIT_MAX']) ) {
		$crit_max = $VAL['CRIT_MAX'];
	}
	if ( $VAL['CRIT_MIN'] != "" && is_numeric($VAL['CRIT_MIN']) ) {
		$crit_min = $VAL['CRIT_MIN'];
	}
	if ( $VAL['MIN'] != "" && is_numeric($VAL['MIN']) ) {
		$lower = " --lower=" . $VAL['MIN'];
		$minimum = $VAL['MIN'];
	}
	if ( $VAL['MAX'] != "" && is_numeric($VAL['MAX']) ) {
		$maximum = $VAL['MAX'];
	}
	if ($VAL['UNIT'] == "%%") {
		$vlabel = "%";
		$upper = " --upper=101 ";
		$lower = " --lower=0 ";
	}
	else {
		$vlabel = $VAL['UNIT'];
	}

	$opt[$KEY] = '--vertical-label "' . $vlabel . '" --title "' . $this->MACRO['DISP_HOSTNAME'] . ' / ' . $this->MACRO['DISP_SERVICEDESC'] . '"' . $upper . $lower;
	$ds_name[$KEY] = $VAL['LABEL'];
	$def[$KEY]  = rrd::def     ("var1", $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
	$def[$KEY] .= rrd::gradient("var1", "3152A5", "BDC6DE", rrd::cut($VAL['NAME'],16), 20);
	$def[$KEY] .= rrd::line1   ("var1", $_LINE );
	$def[$KEY] .= rrd::gprint  ("var1", array("LAST","MAX","AVERAGE"), "%3.3lf %S".$VAL['UNIT']);
	if ($warning != "") {
		$def[$KEY] .= rrd::hrule($warning, $_WARNRULE, "Warning  $warning \\n");
	}
	if ($warn_min != "") {
		$def[$KEY] .= rrd::hrule($warn_min, $_WARNRULE, "Warning  (min)  $warn_min \\n");
	}
	if ($warn_max != "") {
		$def[$KEY] .= rrd::hrule($warn_max, $_WARNRULE, "Warning  (max)  $warn_max \\n");
	}
	if ($critical != "") {
		$def[$KEY] .= rrd::hrule($critical, $_CRITRULE, "Critical $critical \\n");
	}
	if ($crit_min != "") {
		$def[$KEY] .= rrd::hrule($crit_min, $_CRITRULE, "Critical (min)  $crit_min \\n");
	}
	if ($crit_max != "") {
		$def[$KEY] .= rrd::hrule($crit_max, $_CRITRULE, "Critical (max)  $crit_max \\n");
	}
}
?>
