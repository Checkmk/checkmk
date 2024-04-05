#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_license_usage>>>
# 524288000 5669830


# mypy: disable-error-code="var-annotated"

import collections

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import render

SplunkLicenseUsage = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "SplunkLicenseUsage", ["quota", "slaves_usage_bytes"]
)


def parse_splunk_license_usage(string_table):
    parsed = {}

    for lcs_detail in string_table:
        try:
            quota, slaves_usage_bytes = lcs_detail

            parsed.setdefault("License Usage", []).append(
                SplunkLicenseUsage(int(quota), int(slaves_usage_bytes))
            )

        except (IndexError, ValueError):
            pass

    return parsed


def inventory_splunk_license_usage(parsed):
    yield None, {}


def check_splunk_license_usage(item, params, parsed):
    data = parsed["License Usage"][0]

    yield 0, "Quota: %s" % render.bytes(data.quota)

    warn, crit = params["usage_bytes"]

    for value, infotext in [(data.slaves_usage_bytes, "Slaves usage")]:
        if isinstance(warn, float):
            warn = data.quota / 100 * warn
            crit = data.quota / 100 * crit

        yield check_levels(
            value,
            "splunk_slave_usage_bytes",
            (warn, crit),
            human_readable_func=render.bytes,
            infoname=infotext,
        )


check_info["splunk_license_usage"] = LegacyCheckDefinition(
    parse_function=parse_splunk_license_usage,
    service_name="Splunk License Usage",
    discovery_function=inventory_splunk_license_usage,
    check_function=check_splunk_license_usage,
    check_ruleset_name="splunk_license_usage",
    check_default_parameters={
        "usage_bytes": (80.0, 90.0),
    },
)
