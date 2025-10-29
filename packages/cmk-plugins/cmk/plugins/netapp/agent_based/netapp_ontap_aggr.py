#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.netapp import models

Section = Mapping[str, models.AggregateModel]

# <<<netapp_ontap_aggr:sep(0)>>>
# {
#     "name": "aggr1_mcc_darz_a_02_data",
#     "space": {"block_storage": {"available": 13103519227904, "size": 13131644821504}},
# }
# {
#     "name": "aggr1_mcc_darz_a_01_data",
#     "space": {"block_storage": {"available": 12804446429184, "size": 13131644821504}},
# }


def parse_netapp_ontap_aggr(string_table: StringTable) -> Section:
    aggregates = {}
    for line in string_table:
        agg = models.AggregateModel.model_validate_json(line[0])
        aggregates[agg.name] = agg

    return aggregates


agent_section_netapp_ontap_aggr = AgentSection(
    name="netapp_ontap_aggr",
    parse_function=parse_netapp_ontap_aggr,
)


def discovery_netapp_ontap_aggr(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_netapp_ontap_aggr(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (
        not (aggr := section.get(item))
        or aggr.space.block_storage.size is None
        or aggr.space.block_storage.available is None
    ):
        return

    fslist_blocks = [(item, aggr.size_total(), aggr.size_avail(), 0)]
    yield from df_check_filesystem_list(get_value_store(), item, params, fslist_blocks)


check_plugin_netapp_ontap_aggr = CheckPlugin(
    name="netapp_ontap_aggr",
    service_name="Aggregation %s",
    discovery_function=discovery_netapp_ontap_aggr,
    check_function=check_netapp_ontap_aggr,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
