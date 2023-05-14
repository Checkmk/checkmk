#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.fireeye import inventory_fireeye_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.fireeye import DETECT

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


check_info["fireeye_lic_active"] = LegacyCheckDefinition(
    detect=DETECT,
    discovery_function=lambda info: inventory_fireeye_generic(info, False),
    check_function=check_fireeye_lic_active,
    service_name="Active Licenses",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1",
        oids=["10", "11", "12"],
    ),
)
