#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.stormshield import DETECT_STORMSHIELD


def inventory_stormshield_info(info):
    yield "Stormshield Info", None


def check_stormshield_info(item, params, info):
    for model, version, serial, sysname, syslanguage in info:
        yield 0, "Model: {}, Version: {}, Serial: {}, SysName: {}, \
            SysLanguage: {}".format(
            model,
            version,
            serial,
            sysname,
            syslanguage,
        )


def parse_stormshield_info(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["stormshield_info"] = LegacyCheckDefinition(
    parse_function=parse_stormshield_info,
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.0",
        oids=["1", "2", "3", "4", "5"],
    ),
    service_name="%s",
    discovery_function=inventory_stormshield_info,
    check_function=check_stormshield_info,
)
