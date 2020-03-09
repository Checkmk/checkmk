<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

setlocale(LC_ALL, "POSIX");

// Make data sources available via names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n]     = "$RRDFILE[$i]:$DS[$i]:MAX";
    $RRD_MIN[$n] = "$RRDFILE[$i]:$DS[$i]:MIN";
    $RRD_AVG[$n] = "$RRDFILE[$i]:$DS[$i]:AVERAGE";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

# RRDtool Options
#$servicedes=$NAGIOS_SERVICEDESC

$fsname = str_replace("_", "/", substr($servicedesc, 3));
$fstitle = $fsname;

# Hack for windows: replace C// with C:\
if (strlen($fsname) == 3 && substr($fsname, 1, 2) == '//') {
    $fsname = $fsname[0] . "\:\\\\";
    $fstitle = $fsname[0] . ":\\";
}

$sizegb = sprintf("%.1f", $MAX[1] / 1024.0);
$maxgb = $MAX[1] / 1024.0;
$warngb = $WARN[1] / 1024.0;
$critgb = $CRIT[1] / 1024.0;
$warngbtxt = sprintf("%.1f", $warngb);
$critgbtxt = sprintf("%.1f", $critgb);

$opt[1] = "--vertical-label GB -l 0 -u $maxgb --title '$hostname: $servicedesc ($sizegb GB)' ";

# First graph show current filesystem usage
$def[1] = "DEF:mb=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:var1=mb,1024,/ ";
$def[1] .= "AREA:var1#00ffc6:\"used space on $fsname\\n\" ";

# Optional uncommitted usage e.g. for esx hosts
if(isset($RRD['uncommitted'])) {
    $def[1] .= "DEF:uncommitted_mb=".$RRD['uncommitted']." ";
    $def[1] .= "CDEF:uncommitted_gb=uncommitted_mb,1024,/ ";
    $def[1] .= "CDEF:total_gb=uncommitted_gb,var1,+ ";
} else {
    $def[1] .= "CDEF:total_gb=var1 ";
}

$def[1] .= "HRULE:$maxgb#003300:\"Size ($sizegb GB) \" ";
$def[1] .= "HRULE:$warngb#ffff00:\"Warning at $warngbtxt GB \" ";
$def[1] .= "HRULE:$critgb#ff0000:\"Critical at $critgbtxt GB \\n\" ";
$def[1] .= "GPRINT:var1:LAST:\"current\: %6.2lf GB\" ";
$def[1] .= "GPRINT:var1:MAX:\"max\: %6.2lf GB \" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"avg\: %6.2lf GB\\n\" ";

if(isset($RRD['uncommitted'])) {
    $def[1] .= "AREA:uncommitted_gb#eeccff:\"Uncommited\":STACK ";
    $def[1] .= "GPRINT:uncommitted_gb:MAX:\"%6.2lf GB\l\" ";
}

$def[1] .= "LINE1:total_gb#226600 ";

# Second graph is optional and shows trend. The MAX field
# of the third variable contains (size of the filesystem in MB
# / range in hours). From that we can compute the configured range.
if (isset($RRD['growth'])) {
    $size_mb_per_hours = floatval($MAX['trend']); // this is size_mb / range(hours)
    $size_mb = floatval($MAX[1]);
    $hours = 1.0 / ($size_mb_per_hours / $size_mb);
    $range = sprintf("%.0fh", $hours);

    // Current growth / shrinking. This value is give as MB / 24 hours.
    // Note: This has changed in 1.1.13i3. Prior it was MB / trend_range!
    $opt[2] = "--vertical-label '+/- MB / 24h' -l -1 -u 1 -X0 --title '$hostname: Growth of $servicedesc' ";
    $def[2] = "DEF:growth_max=${RRD['growth']} ";
    $def[2] .= "DEF:growth_min=${RRD_MIN['growth']} ";
    $def[2] .= "DEF:trend=${RRD_AVG['trend']} ";
    $def[2] .= "CDEF:growth_pos=growth_max,0,MAX ";
    $def[2] .= "CDEF:growth_neg=growth_min,0,MIN ";
    $def[2] .= "CDEF:growth_minabs=0,growth_min,- ";
    $def[2] .= "CDEF:growth=growth_minabs,growth_max,MAX ";
    $def[2] .= "HRULE:0#c0c0c0 ";
    $def[2] .= "AREA:growth_pos#3060f0:\"Grow\" ";
    $def[2] .= "AREA:growth_neg#30f060:\"Shrink \" ";
    $def[2] .= "GPRINT:growth:LAST:\"Current\: %+9.2lfMB / 24h\" ";
    $def[2] .= "GPRINT:growth:MAX:\"Max\: %+9.2lfMB / 24h\\n\" ";

    // Trend
    $opt[3] = "--vertical-label '+/- MB / 24h' -l -1 -u 1 -X0 --title '$hostname: Trend for $servicedesc' ";
    $def[3] = "DEF:trend=${RRD_AVG['trend']} ";
    $def[3] .= "HRULE:0#c0c0c0 ";
    $def[3] .= "LINE1:trend#000000:\"Trend\:\" ";
    $def[3] .= "GPRINT:trend:LAST:\"%+7.2lf MB/24h\" ";
    if ($WARN['trend']) {
        $warn_mb = sprintf("%.2fMB", $WARN['trend'] * $hours / 24.0);
        $def[3] .= "LINE1:${WARN['trend']}#ffff00:\"Warn\: $warn_mb / $range\" ";
    }
    if ($CRIT['trend']) {
        $crit_mb = sprintf("%.2fMB", $CRIT['trend'] * $hours / 24.0);
        $def[3] .= "LINE1:${CRIT['trend']}#ff0000:\"Crit\: $crit_mb / $range\" ";
    }
    $def[3] .= "COMMENT:\"\\n\" ";
}

if (isset($RRD['trend_hoursleft'])) {
    // Trend
    $opt[4] = "--vertical-label 'Days left' -l -1 -u 365 -X0 --title '$hostname: Days left for $servicedesc' ";
    $def[4] = "DEF:hours_left=${RRD_AVG['trend_hoursleft']} ";
    $def[4] .= "DEF:hours_left_min=${RRD_MIN['trend_hoursleft']} ";
    // negative hours indicate no growth
    // the dataset hours_left_isneg stores this info for each point as True/False
    $def[4] .= "CDEF:hours_left_isneg=hours_left_min,-1,EQ ";
    $def[4] .= "CDEF:hours_left_unmon=hours_left_min,400,0,IF ";
    $def[4] .= "CDEF:days_left=hours_left,24,/ ";
    $def[4] .= "CDEF:days_left_cap=days_left,400,MIN ";
    // Convert negative points to 400 (y-axis cap)
    $def[4] .= "CDEF:days_left_cap_positive=hours_left_isneg,400,days_left_cap,IF ";
    // The AREA has a rendering problem. Points are too far to the right
    $def[4] .= "AREA:hours_left_unmon#AA2200: ";

    $def[4] .= "AREA:days_left_cap_positive#22AA44:\"Days left\:\" ";
    if ($ACT[4] == -1)
    {
        $def[4] .= "COMMENT:\"Not growing\" ";
    }
    else {
        $def[4] .= "GPRINT:days_left:LAST:\"%7.2lf days\" ";
    }
}

?>
