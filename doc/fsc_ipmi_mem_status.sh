#!/bin/bash
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
# Author: Lars Michelsen <lm@mathias-kettner.de>
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

# This is a check_mk_agent plugin. It reads the memory module status
# information from IPMI on FSC TX 120 systems (and maybe others) using
# ipmi-sensors and ipmi-raw commands.
#
# This plugin has been developed on FSC TX 120 but may also work on
# other FSC hardware platforms. Please tell us when you find some
# other software where this plugin outputs valid information
#
# The plugin has been tested with freeipmi 0.5.1 and 0.8.4. Other
# versions may work too but have not been used during implementation.
#
# To enable this plugin simply copy it to the plugins directory of
# check_mk_agent on your target machines. By default the directory
# is located here: /usr/lib/check_mk_agent/plugins

# Check needed binarys
which ipmi-sensors >/dev/null 2>&1
[ $? -ne 0 ] && echo "E ipmi-sensors is missing" && exit 1

which ipmi-raw >/dev/null 2>&1
[ $? -ne 0 ] && echo "E ipmi-raw is missing" && exit 1

FORMAT=
if [[ "$(ipmi-sensors -V | head -1)" =~ "ipmi-sensors - 0.8.*" ]]; then
  FORMAT="--legacy-output"
fi
SLOTS="$(ipmi-sensors -g OEM_Reserved $FORMAT | grep DIMM | cut -d' ' -f 2 | uniq)"

# Use ipmi-sensors to get all memory slots of TX-120
OUT=
I=0
for NAME in $SLOTS; do
  STATUS=$(ipmi-raw 0 0x2e 0xf5 0x80 0x28 0x00 0x48 $I | cut -d' ' -f 7)
  OUT="$OUT\n$I $NAME $STATUS"
  I=$(($I+1))
done

# Only print output when at least one memory slot was found
if [ $I -ne 0 ]; then
  echo -n "<<<fsc_ipmi_mem_status>>>"
  echo -e "$OUT"
fi

exit 0
