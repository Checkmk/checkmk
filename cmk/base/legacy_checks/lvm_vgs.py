#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.config import check_info, factory_settings

factory_settings["filesystem_default_levels"] = FILESYSTEM_DEFAULT_PARAMS


def inventory_lvm_vgs(info):
    for line in info:
        yield line[0], {}


def check_lvm_vgs(item, params, info):
    vglist = []
    for vg, _pvs, _lvs, _sns, _attr, size, free in info:
        size_mb = int(size) // 1024**2
        avail_mb = int(free) // 1024**2
        vglist.append((vg, size_mb, avail_mb, 0))
    return df_check_filesystem_list(item, params, vglist)


check_info["lvm_vgs"] = LegacyCheckDefinition(
    check_function=check_lvm_vgs,
    discovery_function=inventory_lvm_vgs,
    service_name="LVM VG %s",
    check_ruleset_name="volume_groups",
    default_levels_variable="filesystem_default_levels",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
