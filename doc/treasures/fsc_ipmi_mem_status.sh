#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

# shellcheck disable=SC2230 # which is non-standard. Use builtin 'command -v' instead.

# Check needed binarys
if ! which ipmi-sensors >/dev/null 2>&1; then
    OUT="\nE ipmi-sensors is missing" && ERR=1
fi
if ! which ipmi-raw >/dev/null 2>&1; then
    OUT="\nE ipmi-raw is missing" && ERR=1
fi

if [ -z $ERR ]; then
    # No cache file existing? => give more time to create it
    if [ ! -e "/var/cache/.freeipmi/sdr-cache/sdr-cache-$(hostname).127.0.0.1" ]; then
        TIMEOUT=50
    else
        TIMEOUT=2
    fi
    CMD="waitmax $TIMEOUT ipmi-sensors --sdr-cache-directory /var/cache -g OEM_Reserved $FORMAT"
    CMD="ipmi-sensors --sdr-cache-directory /var/cache -g OEM_Reserved $FORMAT"
    FORMAT="--legacy-output"
    SENSORS=$($CMD $FORMAT 2>&1 || $CMD 2>&1)

    # Check for caching problem
    if [[ "$SENSORS" =~ "SDR" ]]; then
        OUT="\nE SDR cache broken. Need to be flushed and reloaded"
        ERR=1
    fi

    if [ -z $ERR ]; then
        SLOTS="$(echo "$SENSORS" | grep DIMM | cut -d' ' -f 2 | uniq)"

        # Use ipmi-sensors to get all memory slots of TX-120
        OUT=
        I=0
        for NAME in $SLOTS; do
            STATUS=$(ipmi-raw 0 0x2e 0xf5 0x80 0x28 0x00 0x48 $I | cut -d' ' -f 7)
            OUT="$OUT\n$I $NAME $STATUS"
            I=$((I + 1))
        done
    fi
fi

# Only print output when at least one memory slot was found
if [ -n "$ERR" ] || [ "$I" != "0" ]; then
    echo -n "<<<fsc_ipmi_mem_status>>>"
    echo -e "$OUT"
fi

exit 0
