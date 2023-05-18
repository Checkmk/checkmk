#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.check_legacy_includes.netapp_api import netapp_api_parse_lines
from cmk.base.config import check_info

# <<<netapp_api_aggr:sep(9)>>>
# aggregation aggr0_root_n1       size-available 940666880        size-total 1793064960
# aggregation aggr0_root_n2       size-available 940556288        size-total 1793064960
# aggregation aggr1_n1    size-available 2915315712       size-total 9437184000
# aggregation aggr1_n2    size-available 2936561664       size-total 9437184000


def inventory_netapp_api_aggr(parsed):
    for name, aggr in parsed.items():
        if "size-total" in aggr and "size-available" in aggr:
            yield name, {}


@get_parsed_item_data
def check_netapp_api_aggr(item, params, aggr):
    if not ("size-total" in aggr and "size-available" in aggr):
        return None
    mega = 1024.0 * 1024.0
    size_total = int(aggr.get("size-total")) / mega  # fixed: true-division
    size_avail = int(aggr.get("size-available")) / mega  # fixed: true-division
    return df_check_filesystem_list(item, params, [(item, size_total, size_avail, 0)])


check_info["netapp_api_aggr"] = LegacyCheckDefinition(
    check_function=check_netapp_api_aggr,
    parse_function=netapp_api_parse_lines,
    discovery_function=inventory_netapp_api_aggr,
    service_name="Aggregation %s",
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
