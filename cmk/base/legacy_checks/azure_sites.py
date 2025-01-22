#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.azure import (
    check_azure_metric,
    get_data_or_go_stale,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import Service
from cmk.plugins.lib.azure import (
    get_service_labels_from_resource_tags,
    iter_resource_attributes,
    parse_resources,
)

check_info = {}

_AZURE_SITES_METRICS = (  # metric_key, cmk_key, display_name, use_rate_flag
    ("total_CpuTime", "cpu_time_percent", "CPU time", True),
    ("total_AverageResponseTime", "avg_response_time", "Average response time", False),
    ("total_Http5xx", "error_rate", "Rate of server errors", True),
)


def check_azure_sites(item, params, section):
    resource = get_data_or_go_stale(item, section)
    for key, cmk_key, displ, use_rate in _AZURE_SITES_METRICS:
        levels = params.get("%s_levels" % cmk_key, (None, None))
        mcheck = check_azure_metric(resource, key, cmk_key, displ, levels=levels, use_rate=use_rate)
        if mcheck:
            yield mcheck

    for kv_pair in iter_resource_attributes(resource):
        yield 0, "%s: %s" % kv_pair


def discover_azure_sites(section):
    yield from (
        Service(item=item, labels=get_service_labels_from_resource_tags(resource.tags))
        for item, resource in section.items()
    )


check_info["azure_sites"] = LegacyCheckDefinition(
    name="azure_sites",
    parse_function=parse_resources,
    service_name="Site %s",
    discovery_function=discover_azure_sites,
    check_function=check_azure_sites,
    check_ruleset_name="webserver",
    check_default_parameters={
        # https://www.nngroup.com/articles/response-times-3-important-limits/
        "avg_response_time_levels": (1.0, 10.0),
        # https://www.unigma.com/2016/07/11/best-practices-for-monitoring-microsoft-azure/
        "error_rate_levels": (0.01, 0.04),
        "cpu_time_percent_levels": (85.0, 95.0),
    },
)
