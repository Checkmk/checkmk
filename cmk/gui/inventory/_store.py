#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helpers to access the stored inventory data"""

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.structured_data import InventoryPaths


def has_inventory(host_name: HostName) -> bool:
    return (
        InventoryPaths(cmk.utils.paths.omd_root).inventory_tree(host_name).exists()
        if host_name
        else False
    )
