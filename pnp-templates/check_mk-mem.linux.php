<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

$defopt = "--vertical-label 'Bytes' -l0 -b 1024 ".
          "--color MGRID\"#cccccc\" --color GRID\"#dddddd\" ";

# Work with names rather then numbers.
global $mem_defines;
$mem_defines = array();
foreach ($NAME as $i => $n) {
    $mem_defines[$n] = "DEF:$n=$RRDFILE[$i]:$DS[$i]:MAX ";
}

function mem_area($varname, $color, $title, $stacked)
{
    return mem_curve("AREA", $varname, $color, $title, $stacked);
}

function mem_line($varname, $color, $title, $stacked)
{
    return mem_curve("LINE1", $varname, $color, $title, $stacked);
}

function mem_curve($how, $varname, $color, $title, $stacked)
{
    global $mem_defines;
    $tit = sprintf("%-30s", $title);
    if (isset($mem_defines[$varname])) {
        $x = $mem_defines[$varname] . "$how:$varname#$color:\"$tit\"";
        if ($stacked)
            $x .= ":STACK";
        $x .= " ";
        $x .= "CDEF:${varname}_gb=$varname,1073741824,/ ";
        $x .= "GPRINT:${varname}_gb:LAST:\"%6.1lf GB last\" ";
        $x .= "GPRINT:${varname}_gb:AVERAGE:\"%6.1lf GB avg\" ";
        $x .= "GPRINT:${varname}_gb:MAX:\"%6.1lf GB max\\n\" ";
        return $x;
    }
    else {
        return "";
    }
}


# 1. Overview
$opt[] = $defopt . "--title \"RAM + Swap overview\"";
$def[] = ""
        . mem_area("mem_total",    "f0f0f0", "RAM installed",     FALSE)
        . mem_area("swap_total",   "e0e0e0", "Swap installed",     TRUE)
        . mem_area("mem_used",     "80ff40", "RAM used",          FALSE)
        . mem_area("swap_used",    "408f20", "Swap used",          TRUE)
        ;

# 2. Swap
$opt[] = $defopt . "--title \"Swap\"";
$def[] = ""
        . mem_area("swap_total",   "e0e0e0", "Swap installed",    FALSE)
        . mem_area("swap_used",    "408f20", "Swap used",         FALSE)
        . mem_area("swap_cached",  "5bebc9", "Swap cached",        TRUE)
        ;

# 3. Caches
$opt[] = $defopt . "--title \"Caches\"";
$def[] = ""
        . mem_area("cached",       "91cceb", "File contents",   FALSE)
        . mem_area("buffers",      "5bb9eb", "Filesystem structure",        TRUE)
        . mem_area("swap_cached",  "5bebc9", "Swap cached",        TRUE)
        . mem_area("slab",         "af91eb", "Slab (Various smaller caches)",        TRUE)
        ;

# 4. Active & Inactive
$opt[] = $defopt . "--title \"Active and Inactive Memory\"";
if (isset($mem_defines["active_anon"])) {
    $def[] = ""
            . mem_area("active_anon",      "ff4040", "Active   (anonymous)",   FALSE)
            . mem_area("active_file",      "ff8080", "Active   (files)",       TRUE)
            . mem_area("inactive_anon",    "377cab", "Inactive (anonymous)",   FALSE)
            . mem_area("inactive_file",    "4eb0f2", "Inactive (files)",       TRUE)
            ;
}
else {
    $def[] = ""
            . mem_area("active",      "ff4040", "Active",   FALSE)
            . mem_area("inactive",    "4040ff", "Inactive",   FALSE)
            ;
}

# 5. Dirty
$opt[] = $defopt . "--title \"Filesystem Writeback\"";
$def[] = ""
        . mem_area("dirty",         "f2904e", "Dirty disk blocks",   FALSE)
        . mem_area("writeback",     "f2df40", "Currently being written",   TRUE)
        . mem_area("nfs_unstable",  "c6f24e", "Modified NFS data",        TRUE)
        . mem_area("bounce",        "4ef26c", "Bounce buffers",        TRUE)
        . mem_area("writeback_tmp", "4eeaf2", "Dirty FUSE data",        TRUE)
        ;

# 6. Committing
if (isset($mem_defines["commit_limit"])) {
    $opt[] = $defopt . "--title \"Memory committing\"";
    $def[] = ""
            . mem_area("total_total",   "f0f0f0", "Total virtual memory",   FALSE)
            . mem_area("committed_as",  "40a080", "Committed memory",       FALSE)
            . mem_area("commit_limit",  "e0e0e0", "Commit limit",            TRUE)
            ;
}

# 7. Shared memory
if (isset($mem_defines["shmem"])) {
    $opt[] = $defopt . "--title \"Shared memory\"";
    $def[] = ""
            . mem_area("shmem",   "bf9111", "Shared memory",            FALSE)
            ;
}

# 8. Unswappable memory
$opt[] = $defopt . "--title \"Memory that cannot be swapped out\"";
$def[] = ""
        . mem_area("kernel_stack",  "7192ad", "Kernel stack",           FALSE)
        . mem_area("page_tables",   "71ad9f", "Page tables",             TRUE)
        . mem_area("mlocked",       "a671ad", "Locked mmap() data",      TRUE)
        ;

# 9. Huge Pages
if (isset($mem_defines["huge_pages_total"])) {
$opt[] = $defopt . "--title \"Huge Pages\"";
    $def[] = ""
            . mem_area("huge_pages_total",  "f0f0f0", "Total",  FALSE)
            . mem_area("huge_pages_free",   "f0a0f0", "Free",   FALSE)
            . mem_area("huge_pages_rsvd",   "40f0f0", "Reserved part of Free",  FALSE)
            . mem_line("huge_pages_surp",   "90f0b0", "Surplus",  TRUE)
            ;
}

# 10. VMalloc
if (isset($mem_defines["vmalloc_total"])) {
    $opt[] = $defopt . "--title \"VMalloc Address Space\"";
    $def[] = ""
        . mem_area("vmalloc_total",  "f0f0f0", "Total address space",   FALSE)
        . mem_area("vmalloc_used",   "aaf76f", "Allocated space",       FALSE)
        . mem_area("vmalloc_chunk",  "c6f7e9", "Largest free chunk",     TRUE)
        ;
}

?>
