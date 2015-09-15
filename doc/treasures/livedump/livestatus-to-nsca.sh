#!/bin/sh
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

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
Filter: obsess_over_service = 1" | unixcat $LiveStatusPipe | tr \; "\t" |  $NscaBin $NagiosHost -c $NscaCfg
