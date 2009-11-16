<?php
# +------------------------------------------------------------------+
# |                     _           _           _                    |
# |                  __| |_  ___ __| |__  _ __ | |__                 |
# |                 / _| ' \/ -_) _| / / | '  \| / /                 |
# |                 \__|_||_\___\__|_\_\_|_|_|_|_\_\                 |
# |                                   |___|                          |
# |              _   _   __  _         _        _ ____               |
# |             / | / | /  \| |__  ___| |_ __ _/ |__  |              |
# |             | |_| || () | '_ \/ -_)  _/ _` | | / /               |
# |             |_(_)_(_)__/|_.__/\___|\__\__,_|_|/_/                |
# |                                            check_mk 1.1.0beta17  |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
# 
# This file is part of check_mk 1.1.0beta17.
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

$opt[1] = "--vertical-label Load -l0  -u 1 --title \"CPU Load for $hostname / $servicedesc\" ";

$def[1] =  "DEF:var1=$rrdfile:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:var2=$rrdfile:$DS[2]:AVERAGE " ;
$def[1] .= "DEF:var3=$rrdfile:$DS[3]:AVERAGE " ;
$def[1] .= "HRULE:$WARN[1]#FFFF00 ";
$def[1] .= "HRULE:$CRIT[1]#FF0000 ";
$def[1] .= "AREA:var1#60c0e0:\"Load average  1 min \" " ;
$def[1] .= "GPRINT:var1:LAST:\"%6.2lf last\" " ;
$def[1] .= "GPRINT:var1:AVERAGE:\"%6.2lf avg\" " ;
$def[1] .= "GPRINT:var1:MAX:\"%6.2lf max\\n\" ";
$def[1] .= "LINE:var3#004080:\"Load average 15 min \" " ;
$def[1] .= "GPRINT:var3:LAST:\"%6.2lf last\" " ;
$def[1] .= "GPRINT:var3:AVERAGE:\"%6.2lf avg\" " ;
$def[1] .= "GPRINT:var3:MAX:\"%6.2lf max\\n\" " ;
?>
