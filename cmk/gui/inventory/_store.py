#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Helpers to access the stored inventory data"""

import os

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths


def has_inventory(hostname: HostName) -> bool:
    return (
        os.path.exists(f"{cmk.utils.paths.inventory_output_dir}/{hostname}") if hostname else False
    )
