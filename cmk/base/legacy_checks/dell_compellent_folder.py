#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.dell import DETECT_DELL_COMPELLENT


def inventory_dell_compellent_folder(info):
    for line in info:
        if line[1] and float(line[1]) != 0:
            yield (line[0], {})


def check_dell_compellent_folder(item, params, info):
    for number, total, used in info:
        if number == item:
            # sizes delivered in GiB
            total = float(total) * 1024
            free = total - float(used) * 1024
            yield df_check_filesystem_list(item, params, [(item, total, free, 0)])


check_info["dell_compellent_folder"] = LegacyCheckDefinition(
    detect=DETECT_DELL_COMPELLENT,
    discovery_function=inventory_dell_compellent_folder,
    check_function=check_dell_compellent_folder,
    service_name="Folder %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.11000.2000.500.1.2.32.1",
        oids=["2", "5", "6"],
    ),
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
