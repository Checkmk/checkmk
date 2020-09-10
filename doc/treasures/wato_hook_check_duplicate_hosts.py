#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This hook scans the whole WATO configuration for duplicate hosts having
# duplicate names or IP addresses and warns the admin about this fact.

# Put this script into local/share/check_mk/web/plugins/wato on a Checkmk site
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
