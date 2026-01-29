#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.fireeye.lib import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.11.5.1.10.0 1
# .1.3.6.1.4.1.25597.11.5.1.11.0 1
# .1.3.6.1.4.1.25597.11.5.1.12.0 1


def check_fireeye_lic_active(_no_item, _no_params, info):
    product, content, support = info[0]
    for feature, value in [("Product", product), ("Content", content), ("Support", support)]:
        if value == "1":
            yield 0, "%s license active" % feature
        else:
            yield 2, "%s license not active" % feature


def parse_fireeye_lic_active(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_lic_active(info):
    yield from [(None, None)] if info else []


check_info["fireeye_lic_active"] = LegacyCheckDefinition(
    name="fireeye_lic_active",
    parse_function=parse_fireeye_lic_active,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1",
        oids=["10", "11", "12"],
    ),
    service_name="Active Licenses",
    discovery_function=discover_fireeye_lic_active,
    check_function=check_fireeye_lic_active,
)
