#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import cmk

# Settings for new rule based notifications
enable_rulebased_notifications = False
notification_fallback_email    = ""
notification_rules             = []
# Check every 10 seconds for ripe bulks
notification_bulk_interval     = 10
notification_plugin_timeout    = 60

# Notification Spooling.

# Possible values for notification_spooling
# "off"    - Direct local delivery without spooling
# "local"  - Asynchronous local delivery by notification spooler
# "remote" - Forward to remote site by notification spooler
# "both"   - Asynchronous local delivery plus remote forwarding
# False    - legacy: sync delivery  (and notification_spool_to)
# True     - legacy: async delivery (and notification_spool_to)
if cmk.is_raw_edition():
    notification_spooling = "off"
else:
    notification_spooling = "local"

# Legacy setting. The spool target is now specified in the
# configuration of the spooler. notification_spool_to has
# the tuple format (remote_host, tcp_port, also_local)
notification_spool_to = None


