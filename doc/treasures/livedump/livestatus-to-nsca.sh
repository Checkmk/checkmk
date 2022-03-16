#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A helper script that build a bridge between modern livedump
# for state export while still using legacy NSCA as transport.
# if NSCA is not a strict requirement, walk on and try livedump!

# Advantages:
# - automagic detection of NSCA-enabled devices
# - use one bulk transfer even with NCSA
# - can run every minute

# Disadvantages:
# - still using NSCA
# - still have to maintain the config on the NSCA receiver.

# Edit these parameters and the livestatus path to match your submission config
# or source them from your submit script.
NagiosDir="/usr/local/nagios"
NscaBin="$NagiosDir/libexec/send_nsca"
NscaCfg="$NagiosDir/etc/send_nsca.cfg"
LiveStatusPipe="$NagiosDir/var/rw/livestatus.cmd"
NagiosHost="nagioshost"

# Add obsess_over_host = 1 to your filter if you wish to supress superfluous hosts.
echo "GET services
Columns: host_name description state plugin_output
Filter: obsess_over_service = 1" | unixcat $LiveStatusPipe | tr \; "\t" | $NscaBin $NagiosHost -c $NscaCfg
