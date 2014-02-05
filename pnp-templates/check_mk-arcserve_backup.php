<?php
#
# Copyright (c) 2006-2010 Joerg Linge (http://www.pnp4nagios.org)
# Default Template used if no other template is found.
# Don`t delete this file ! 
#
# Define some colors ..
#
$_AREA     = '#256aef';
$_LINE     = '#000000';

$_start_color = array("808005", "000080", "000000");
$_end_color   = array("C0C0C0", "BDC6DE", "BDC6DE");

foreach ($this->DS as $KEY=>$VAL) {

	$vlabel   = " ";
	$lower    = "";
	$upper    = "";
	
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
	$def[$KEY] .= rrd::gradient("var1", $_start_color[$KEY], $_end_color[$KEY], rrd::cut($VAL['NAME'],16), 20);
	$def[$KEY] .= rrd::line1   ("var1", $_LINE );
	$def[$KEY] .= rrd::gprint  ("var1", array("LAST","MAX","AVERAGE"), "%3.2lf %S".$VAL['UNIT']);
}
?>
