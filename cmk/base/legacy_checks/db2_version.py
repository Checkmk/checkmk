#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<db2_version>>>
# db2taddm DB2v10.1.0.4,s140509(IP23577)


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_db2_version(info):
    for line in info:
        yield line[0].split(" ", 1)[0], None


def check_db2_version(item, _no_params, info):
    for line in info:
        tokens = line[0].split(" ", 1)
        if len(tokens) < 2:
            if item == tokens[0]:
                return 3, "No instance information found"
        else:
            instance, version = tokens
            if item == instance:
                return 0, version

    return 2, "Instance is down"


check_info["db2_version"] = LegacyCheckDefinition(
    service_name="DB2 Instance %s",
    check_function=check_db2_version,
    discovery_function=inventory_db2_version,
)
