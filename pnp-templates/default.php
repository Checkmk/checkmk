<?php

# Fetch dynamic PNP template from Check_MK's new metrics system

# avoid redeclaration errors if this file is include multiple times (e.g. by basket)
if (!function_exists('get_apache_port')) {
    function get_apache_port() {
        $path = getenv("OMD_ROOT") . "/etc/omd/site.conf";
        foreach (file($path) as $line) {
            if (strpos($line, "CONFIG_APACHE_TCP_PORT") === 0) {
                list($key, $val) = explode("=", $line);
                return trim($val, "'\n\r");
            }
        }
    }
}

$omd_site = getenv("OMD_SITE");
if ($omd_site) {
    $url = "http://localhost:".get_apache_port()."/$omd_site/check_mk/";
    $template_cache_dir = getenv("OMD_ROOT") . "/var/check_mk/pnp_template_cache";
}
else {
    $url = "http://localhost/check_mk/";
    $template_cache_dir = "/tmp/check_mk_pnp_template_cache";
}

if (!file_exists($template_cache_dir))
    mkdir($template_cache_dir, 0755, TRUE);

# Get the list of performance variables and convert them to a string,
# prepend the command name, # e.g. "check_mk-hr_fs:fs_trend,fs_used,zabelfoobar"
$perf_vars = Array();
foreach ($NAME as $i => $n) {
    $perf_vars[] = $n;
}
sort($perf_vars);
# We have to separate the check command name from the rest on
# the right place, i.d. the first "!", to prevent errors while
# creating the default template, e.g. for the custom check
#
# check-mk-custom!$USER2$/check_mssql_health_new --server $HOSTNAME$ --username=$USER6$
# --password=$USER5$ --mode database-free --name filr --warning 20: --critical 10: --commit
#
# If no "!" exists then $CHECK_COMMAND = $NAGIOS_CHECK_COMMAND
$check_command_parts = explode("!", $NAGIOS_CHECK_COMMAND);
$id_string = $check_command_parts[0] . ":" . implode(",", $perf_vars);

# Get current state of previously cached template data for this ID
$template_cache_path = $template_cache_dir . "/" . md5($id_string);
if (file_exists($template_cache_path)) {
    $age = time() - filemtime($template_cache_path);
    if ($age < 60 * 10)
        $cache_state = "uptodate";
    else
        $cache_state = "stale";
}
else
    $cache_state = "missing";

# cache file missing or stale: try to fetch live template via HTTP
if ($cache_state != "uptodate")
{
    // always speaking to local host, so a small connect timeout is good to
    // catch to long hanging requests when e.g. the system apache is not
    // listening on localhost
    ini_set('default_socket_timeout', 2);
    $fd = @fopen($url . "pnp_template.py?id=" . urlencode($id_string), "r");
    if ($fd) {
        $data = "";
        while (!feof($fd)) {
            $data .= fread($fd, 4096);
        }
        fclose($fd);
        $fd = fopen($template_cache_path, "w");
        fwrite($fd, $data);
        fclose($fd);
        $cache_state = "uptodate";
    }
}

if (!function_exists("replace_cmk_expression")) {
    function replace_cmk_expression($NAME, $MIN, $MAX, $WARN, $CRIT, $text)
    {
        # Replace expressions in the title. This not a full implementation of
        # the complete RPN expression syntax of Check_MK - but sufficient for
        # all used cases.
        foreach ($NAME as $i => $n) {
            $text = str_replace("%($n:min@count)", "$MIN[$i]", $text);
            $text = str_replace("%($n:max@count)", "$MAX[$i]", $text);
            $text = str_replace("%($n:warn@count)", "$WARN[$i]", $text);
            $text = str_replace("%($n:crit@count)", "$CRIT[$i]", $text);
        }
        return $text;
    }
}

# Now read template information from cache file, if present
if (($cache_state == "uptodate" || $cache_state == "stale") && filesize($template_cache_path) > 0) {
    $rrdbase = substr($NAGIOS_XMLFILE, 0, strlen($NAGIOS_XMLFILE) - 4);
    $fd = fopen($template_cache_path, "r");
    while (!feof($fd)) {
        $dsname_line = trim(fgets($fd));
        $option_line = replace_cmk_expression($NAME, $MIN, $MAX, $WARN, $CRIT, trim(fgets($fd)));
        $graph_line = str_replace('$RRDBASE$', $rrdbase, fgets($fd));
        if ($dsname_line && $option_line && $graph_line) {
            $ds_name[] = $dsname_line;
            $opt[] = $option_line;
            $def[] = $graph_line;
        }
    }
    fclose($fd);
}


# PNP Default template starts here...
#
# Copyright (c) 2006-2010 Joerg Linge (http://www.pnp4nagios.org)
# Default Template used if no other template is found.
# Don`t delete this file !
#
# Define some colors ..
#
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

            $opt[$KEY] = '--vertical-label "' . $vlabel . '" --title "' . $this->MACRO['DISP_HOSTNAME'] . ' / ' . $this->MACRO['DISP_SERVICEDESC'] . '"' . $upper . $lower;
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
