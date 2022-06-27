#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=no-else-return

from cmk.base.check_api import host_extra_conf, host_name, saveint
from cmk.base.plugins.agent_based.utils.df import df_discovery

from .df import df_check_filesystem_list, filesystem_groups, inventory_df_exclude_mountpoints

# .1.3.6.1.2.1.25.2.3.1.2.1 .1.3.6.1.2.1.25.2.1.2 --> HOST-RESOURCES-MIB::hrStorageType.1
# .1.3.6.1.2.1.25.2.3.1.2.3 .1.3.6.1.2.1.25.2.1.3 --> HOST-RESOURCES-MIB::hrStorageType.3
# .1.3.6.1.2.1.25.2.3.1.3.1 Physical memory --> HOST-RESOURCES-MIB::hrStorageDescr.1
# .1.3.6.1.2.1.25.2.3.1.3.3 Virtual memory --> HOST-RESOURCES-MIB::hrStorageDescr.3
# .1.3.6.1.2.1.25.2.3.1.4.1 1024 --> HOST-RESOURCES-MIB::hrStorageAllocationUnits.1
# .1.3.6.1.2.1.25.2.3.1.4.3 1024 --> HOST-RESOURCES-MIB::hrStorageAllocationUnits.3
# .1.3.6.1.2.1.25.2.3.1.5.1 8122520 --> HOST-RESOURCES-MIB::hrStorageSize.1
# .1.3.6.1.2.1.25.2.3.1.5.3 21230740 --> HOST-RESOURCES-MIB::hrStorageSize.3
# .1.3.6.1.2.1.25.2.3.1.6.1 7749124 --> HOST-RESOURCES-MIB::hrStorageUsed.1
# .1.3.6.1.2.1.25.2.3.1.6.3 7749124 --> HOST-RESOURCES-MIB::hrStorageUsed.3


# Juniper devices put information about the device into the
# field where we expect the mount point. Ugly. Remove that crap.
def fix_hr_fs_mountpoint(mp):
    mp = mp.replace("\\", "/")
    if "mounted on:" in mp:
        return mp.rsplit(":", 1)[-1].strip()
    elif "Label:" in mp:
        pos = mp.find("Label:")
        return mp[:pos].rstrip()
    return mp


def inventory_hr_fs(info):
    mplist = []
    for hrtype, hrdescr, _hrunits, hrsize, _hrused in info:
        hrdescr = fix_hr_fs_mountpoint(hrdescr)
        # NOTE: These types are defined in the HR-TYPES-MIB.
        #       .1.3.6.1.2.1.25.2.1 +
        #                           +-> .4 "hrStorageFixedDisk"
        if (
            hrtype
            in [
                ".1.3.6.1.2.1.25.2.1.4",
                # This strange value below is needed for VCenter Appliances
                ".1.3.6.1.2.1.25.2.3.1.2.4",
            ]
            and hrdescr not in inventory_df_exclude_mountpoints
            and saveint(hrsize) != 0
        ):
            mplist.append(hrdescr)
    return df_discovery(host_extra_conf(host_name(), filesystem_groups), mplist)


def check_hr_fs(item, params, info):
    fslist = []

    if "Label:" in item or "\\" in item:
        return 3, "check had an incompatible change, please re-discover services on this host"

    for _hrtype, hrdescr, hrunits, hrsize, hrused in info:
        hrdescr = fix_hr_fs_mountpoint(hrdescr)
        if "patterns" in params or item == hrdescr:
            unit_size = saveint(hrunits)
            hrsize = saveint(hrsize)
            if hrsize < 0:
                hrsize = hrsize + 2**32
            size = hrsize * unit_size
            hrused = saveint(hrused)
            if hrused < 0:
                hrused = hrused + 2**32
            used = hrused * unit_size
            size_mb = size / 1048576.0
            used_mb = used / 1048576.0
            avail_mb = size_mb - used_mb
            fslist.append((hrdescr, size_mb, avail_mb, 0))

    return df_check_filesystem_list(item, params, fslist)
