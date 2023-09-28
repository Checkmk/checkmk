#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_plesk_domains(info):
    if info and info[0]:
        return [(None, None)]
    return None


def check_plesk_domains(_no_item, _no_params, info):
    if not info:
        return (1, "No domains configured")
    return (0, "%s" % ",<br>".join([i[0] for i in info]))


check_info["plesk_domains"] = LegacyCheckDefinition(
    service_name="Plesk Domains",
    discovery_function=inventory_plesk_domains,
    check_function=check_plesk_domains,
)
