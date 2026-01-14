#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.dell.lib import DETECT_DELL_COMPELLENT

check_info = {}


def discover_dell_compellent_folder(info):
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


def parse_dell_compellent_folder(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_compellent_folder"] = LegacyCheckDefinition(
    name="dell_compellent_folder",
    parse_function=parse_dell_compellent_folder,
    detect=DETECT_DELL_COMPELLENT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.11000.2000.500.1.2.32.1",
        oids=["2", "5", "6"],
    ),
    service_name="Folder %s",
    discovery_function=discover_dell_compellent_folder,
    check_function=check_dell_compellent_folder,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
