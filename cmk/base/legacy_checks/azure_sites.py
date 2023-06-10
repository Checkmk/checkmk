#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.azure import (
    check_azure_metric,
    get_data_or_go_stale,
    iter_resource_attributes,
    parse_resources,
)
from cmk.base.config import check_info

_AZURE_SITES_METRICS = (  # metric_key, cmk_key, display_name, use_rate_flag
    ("total_CpuTime", "cpu_time_percent", "CPU time", True),
    ("total_AverageResponseTime", "avg_response_time", "Average response time", False),
    ("total_Http5xx", "error_rate", "Rate of server errors", True),
)


@get_data_or_go_stale
def check_azure_sites(_item, params, resource):
    for key, cmk_key, displ, use_rate in _AZURE_SITES_METRICS:
        levels = params.get("%s_levels" % cmk_key, (None, None))
        mcheck = check_azure_metric(resource, key, cmk_key, displ, levels=levels, use_rate=use_rate)
        if mcheck:
            yield mcheck

    for kv_pair in iter_resource_attributes(resource):
        yield 0, "%s: %s" % kv_pair


def discover_azure_sites(section):
    yield from ((item, {}) for item in section)


check_info["azure_sites"] = LegacyCheckDefinition(
    parse_function=parse_resources,
    discovery_function=discover_azure_sites,
    check_function=check_azure_sites,
    service_name="Site %s",
    check_ruleset_name="webserver",
    check_default_parameters={
        # https://www.nngroup.com/articles/response-times-3-important-limits/
        "avg_response_time_levels": (1.0, 10.0),
        # https://www.unigma.com/2016/07/11/best-practices-for-monitoring-microsoft-azure/
        "error_rate_levels": (0.01, 0.04),
        "cpu_time_percent_levels": (85.0, 95.0),
    },
)
