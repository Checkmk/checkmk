#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import saveint

from .df import df_inventory, df_check_filesystem_list


def inventory_df_netapp(info):
    mplist = []
    for volume, size_kb, _used_kb in info:
        if saveint(size_kb) > 0:  # Exclude filesystems with zero size (some snapshots)
            mplist.append(volume)
    return df_inventory(mplist)


def check_df_netapp(item, params, info):
    fslist = []
    for mp, size_kb, used_kb in info:
        if "patterns" in params or item == mp:
            size_mb = int(size_kb) >> 10
            used_mb = int(used_kb) >> 10
            avail_mb = size_mb - used_mb
            fslist.append((mp, size_mb, avail_mb, 0))
    return df_check_filesystem_list(item, params, fslist)


def is_netapp_filer(oid):
    return "ontap" in oid(".1.3.6.1.2.1.1.1.0").lower() or \
           oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.789")
