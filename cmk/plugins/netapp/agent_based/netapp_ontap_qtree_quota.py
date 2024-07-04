#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<netapp_ontap_qtree_quota:sep(0)>>>
# {
#     "hard_limit": 10737418240,
#     "name": "IT",
#     "used_total": 5492535296,
#     "user_name": null,
#     "volume": "mcc_darz_a_svm01_cifs_data01",
# }
# {
#     "hard_limit": 10737418240,
#     "name": "Verwaltung",
#     "used_total": 1546006528,
#     "user_name": null,
#     "volume": "mcc_darz_a_svm01_cifs_data01",
# }

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    StringTable,
)
from cmk.plugins.lib import df, netapp_api
from cmk.plugins.lib.netapp_api import Qtree
from cmk.plugins.netapp import models

Section = Mapping[str, Qtree]


def parse_netapp_ontap_qtree_quota(string_table: StringTable) -> Section:
    qtrees: dict[str, Qtree] = {}

    for line in string_table:
        qtree_quota = models.QtreeQuotaModel.model_validate_json(line[0])
        qtree = Qtree(
            quota=qtree_quota.name or "",
            quota_users=",".join(qtree_quota.users),
            volume=qtree_quota.volume,
            disk_limit=str(qtree_quota.hard_limit) if qtree_quota.hard_limit is not None else "",
            disk_used=str(qtree_quota.used_total) if qtree_quota.used_total is not None else "",
        )
        qtrees[qtree.quota] = qtree

        # item name is configurable, so we add data under both names to the parsed section
        # to make the check function easier
        if qtree.volume:
            qtrees[f"{qtree.volume}/{qtree.quota}"] = qtree

    return qtrees


agent_section_netapp_ontap_qtree_quota = AgentSection(
    name="netapp_ontap_qtree_quota",
    parse_function=parse_netapp_ontap_qtree_quota,
)


def discover_netapp_ontap_qtree_quota(
    params: Mapping[str, Any], section: Section
) -> DiscoveryResult:
    yield from netapp_api.discover_netapp_qtree_quota(params, section)


def check_netapp_ontap_qtree_quota(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    qtree = section.get(item)
    if not qtree:
        return

    yield from netapp_api.check_netapp_qtree_quota(item, qtree, params, get_value_store())


check_plugin_netapp_ontap_qtree_quota = CheckPlugin(
    name="netapp_ontap_qtree_quota",
    service_name="Qtree %s",
    discovery_function=discover_netapp_ontap_qtree_quota,
    discovery_ruleset_name="discovery_qtree",
    discovery_default_parameters={"exclude_volume": False},
    check_function=check_netapp_ontap_qtree_quota,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
)
