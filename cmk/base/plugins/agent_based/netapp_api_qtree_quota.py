#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This special agent is deprecated. Please use netapp_ontap_qtree_quota.
"""

# <<<netapp_api_qtree_quota:sep(9)>>>
# quota user01    quota-type user disk-limit 12288000 quota-users AD\aolov  volume vol_silber2_group_cifs   disk-used 0
# quota user01    quota-type user disk-limit 12288000 quota-users AD\bva    volume vol_silber2_group_cifs   disk-used 0
# quota user01    quota-type user disk-limit 12288000 quota-users AD\cclze    volume vol_silber2_group_cifs   disk-used 0
# quota fdo01   quota-type tree disk-limit 4294967296   volume vol_bronze1_fdo1 disk-used 3544121572
# quota fdo03   quota-type tree disk-limit 2684354560   volume vol_bronze1_fdo2 disk-used 788905236

from collections.abc import Generator, Mapping
from typing import Any

from cmk.plugins.lib import df, netapp_api
from cmk.plugins.lib.netapp_api import Qtree

from .agent_based_api.v1 import get_value_store, register
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Mapping[str, Qtree]


def iter_netapp_api_qtree_quota(
    string_table: StringTable,
) -> Generator[tuple[str, Qtree], None, None]:
    for item, instances in netapp_api.parse_netapp_api_multiple_instances(
        string_table, custom_keys=["quota", "quota-users"]
    ).items():
        for instance in instances:
            if (quota_type := instance.get("quota-type", "")) != "tree":
                # The same netapp quota could exist of both type "tree" and "user",
                # which would mean the "tree" quotas would be overwritten.
                continue
            qtree = Qtree(
                quota=instance.get("quota", ""),
                quota_users=instance.get("quota-users", ""),
                quota_type=quota_type,
                volume=instance.get("volume", ""),
                disk_limit=instance.get("disk-limit", ""),
                disk_used=instance.get("disk-used", ""),
                files_used=instance.get("files-used", ""),
                file_limit=instance.get("file-limit", ""),
            )
            yield item, qtree

            # item name is configurable, so we add data under both names to the parsed section
            # to make the check function easier
            if qtree.volume:
                yield f"{qtree.volume}/{item}", qtree


def parse_netapp_api_qtree_quota(string_table: StringTable) -> Section:
    return dict(iter_netapp_api_qtree_quota(string_table))


def get_item_names(qtree: Qtree):  # type: ignore[no-untyped-def]
    short_name = ".".join([n for n in [qtree.quota, qtree.quota_users] if n])
    long_name = f"{qtree.volume}/{short_name}" if qtree.volume else short_name
    return short_name, long_name


def discover_netapp_api_qtree_quota(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    yield from netapp_api.discover_netapp_qtree_quota(params, section)


def check_netapp_api_qtree_quota(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    qtree = section.get(item)
    if not qtree:
        return

    yield from netapp_api.check_netapp_qtree_quota(item, qtree, params, get_value_store())


register.agent_section(name="netapp_api_qtree_quota", parse_function=parse_netapp_api_qtree_quota)

register.check_plugin(
    name="netapp_api_qtree_quota",
    service_name="Qtree %s",
    discovery_function=discover_netapp_api_qtree_quota,
    discovery_ruleset_name="discovery_qtree",
    discovery_default_parameters={"exclude_volume": False},
    check_function=check_netapp_api_qtree_quota,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
)
