#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_alerts>>>
# 5


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_splunk_alerts(info):
    yield None, {}


def check_splunk_alerts(_no_item, params, info):
    try:
        value = int(info[0][0])
    except (IndexError, ValueError):
        return

    infotext = "Number of fired alerts"

    yield check_levels(
        value, "fired_alerts", params.get("alerts"), human_readable_func=int, infoname=infotext
    )


check_info["splunk_alerts"] = LegacyCheckDefinition(
    service_name="Splunk Alerts",
    discovery_function=inventory_splunk_alerts,
    check_function=check_splunk_alerts,
    check_ruleset_name="splunk_alerts",
)
