#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.wmi import (
    inventory_wmi_table_instances,
    parse_wmi_table,
    wmi_yield_raw_persec,
)
from cmk.base.config import check_info


def check_wmi_webservices(item, params, parsed):
    yield from wmi_yield_raw_persec(
        parsed[""], item, "CurrentConnections", infoname="Connections", perfvar="connections"
    )


check_info["wmi_webservices"] = {
    "discovery_function": lambda p: inventory_wmi_table_instances(  # pylint: disable=unnecessary-lambda
        p
    ),
    "check_function": check_wmi_webservices,
    "parse_function": parse_wmi_table,
    "service_name": "Web Service %s",
}
