<?php

# Perfdaten plus Hostname, servicedesc, etc. zu
# lokalem Multisite-Webservice senden. Antwort ist
# die Liste von allen Graphen, mit jeweils Kommandzeile und Graph-Befehl
# $opt[], $def[]. Oder None -> Kein Graph vorhanden. Fallback
# auf PNP-Template. Auch bei HTTP-Fehler Fallbacken.
# URL, die von localhost
# bei OMD: /site/....
# bei Handinstallation localhost:/check_mk/
#
# Copyright (c) 2006-2010 Joerg Linge (http://www.pnp4nagios.org)
# Default Template used if no other template is found.
# Don`t delete this file !
#
# Define some colors ..
#

$omd_site = getenv("OMD_SITE");
if ($omd_site)
    $url = "http://localhost/$omd_site/check_mk/";
else
    $url = "http://localhost/check_mk/";

# TODO: Timeout handling.
$fd = @fopen($url . "pnp_template.py"
                  . "?host="          . urlencode($hostname)
                  . "&service="       . urlencode($servicedesc)
                  . "&perfdata="      . urlencode($NAGIOS_PERFDATA)
                  . "&check_command=" . urlencode($NAGIOS_CHECK_COMMAND), "r");
if ($fd) {
    while (!feof($fd)) {
        $opt[] = trim(fgets($fd));
        $def[] = trim(fgets($fd));
    }
}
else
{

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

            $opt[$KEY] = '--vertical-label "' . $titel . $vlabel . '" --title "' . $this->MACRO['DISP_HOSTNAME'] . ' / ' . $this->MACRO['DISP_SERVICEDESC'] . '"' . $upper . $lower;
            $ds_name[$KEY] = $VAL['LABEL'];
            $def[$KEY]  = rrd::def     ("var1", $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
            $def[$KEY] .= rrd::gradient("var1", "3152A5", "BDC6DE", rrd::cut($VAL['NAME'],16), 20);
            $def[$KEY] .= rrd::line1   ("var1", $_LINE );
            $def[$KEY] .= rrd::gprint  ("var1", array("LAST","MAX","AVERAGE"), "%3.4lf %S".$VAL['UNIT']);
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
            $def[$KEY] .= rrd::comment("Default Template\\r");
            $def[$KEY] .= rrd::comment("Command " . $VAL['TEMPLATE'] . "\\r");
    }
}

?>
