#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.filerdisks import (
    check_filer_disks,
    FILER_DISKS_CHECK_DEFAULT_PARAMETERS,
)
from cmk.base.config import check_info, factory_settings

# Agent output:
# <<<netapp_api_disk:sep(9)>>>

factory_settings["filer_disks_default_levels"] = FILER_DISKS_CHECK_DEFAULT_PARAMETERS


def inventory_netapp_api_disk_summary(info):
    return [(None, {})]


def check_netapp_api_disk_summary(_no_item, params, section):
    # Convert legacy levels
    if "broken_spare_ratio" in params:
        params = {"failed_spare_ratio": params["broken_spare_ratio"]}

    return check_filer_disks(
        [disk for disk in section if disk.get("raid-state") not in ["remote", "partner"]], params
    )


check_info["netapp_api_disk.summary"] = LegacyCheckDefinition(
    # section is already migrated!
    check_function=check_netapp_api_disk_summary,
    discovery_function=inventory_netapp_api_disk_summary,
    service_name="NetApp Disks Summary",
    check_ruleset_name="netapp_disks",
    default_levels_variable="filer_disks_default_levels",
    check_default_parameters=FILER_DISKS_CHECK_DEFAULT_PARAMETERS,
)
