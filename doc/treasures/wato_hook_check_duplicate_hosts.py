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

# This hook scans the whole WATO configuration for duplicate hosts having
# duplicate names or IP addresses and warns the admin about this fact.

# Put this script into local/share/check_mk/web/plugins/wato on a Check_MK site
# and run "omd reload apache" as site user to ensure the plugin is loaded.
from cmk.gui.log import logger


def pre_activate_changes_check_duplicate_host(hosts):
    addresses = {}

    for host_name, attrs in hosts.items():
        if attrs["ipaddress"]:
            host_names = addresses.setdefault(attrs["ipaddress"], [])
            host_names.append(host_name)

    for address, host_names in addresses.items():
        if len(host_names) > 1:
            message = "The IP address %s is used for multiple hosts: %s" % (address,
                                                                            ", ".join(host_names))
            html.show_warning(message)
            logger.warning(message)


register_hook('pre-activate-changes', pre_activate_changes_check_duplicate_host)
