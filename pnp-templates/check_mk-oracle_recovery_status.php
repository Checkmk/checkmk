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

$opt[1] = "--vertical-label 'Checkpoint age (s)' -l0 --title \"Checkpoint (time since last Checkpoint)\" ";

$def[1] = "DEF:sec=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:checkpoint_age=sec,1,/ ";
$def[1] .= "AREA:checkpoint_age#80f000:\"Checkpoint (s)\" ";
$def[1] .= "LINE:checkpoint_age#408000 ";
$def[1] .= "GPRINT:checkpoint_age:LAST:\"%7.2lf %s LAST\" ";
$def[1] .= "GPRINT:checkpoint_age:MAX:\"%7.2lf %s MAX\" ";
?>
