#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<netapp_api_qtree_quota:sep(9)>>>
# quota user01    quota-type user disk-limit 12288000 quota-users AD\aolov  volume vol_silber2_group_cifs   disk-used 0
# quota user01    quota-type user disk-limit 12288000 quota-users AD\bva    volume vol_silber2_group_cifs   disk-used 0
# quota user01    quota-type user disk-limit 12288000 quota-users AD\cclze    volume vol_silber2_group_cifs   disk-used 0
# quota fdo01   quota-type tree disk-limit 4294967296   volume vol_bronze1_fdo1 disk-used 3544121572
# quota fdo03   quota-type tree disk-limit 2684354560   volume vol_bronze1_fdo2 disk-used 788905236

from typing import Any, Generator, Mapping, NamedTuple, Tuple

from .agent_based_api.v1 import get_value_store, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import df, netapp_api


class Qtree(NamedTuple):
    quota: str
    quota_users: str
    quota_type: str
    volume: str
    disk_limit: str
    disk_used: str
    files_used: str
    file_limit: str


Section = Mapping[str, Qtree]


def iter_netapp_api_qtree_quota(
    string_table: StringTable,
) -> Generator[Tuple[str, Qtree], None, None]:
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


def get_item_names(qtree: Qtree):
    short_name = ".".join([n for n in [qtree.quota, qtree.quota_users] if n])
    long_name = f"{qtree.volume}/{short_name}" if qtree.volume else short_name
    return short_name, long_name


def discover_netapp_api_qtree_quota(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    exclude_volume = params.get("exclude_volume", False)
    for name, qtree in section.items():
        if qtree.disk_limit.isdigit():
            short_name, long_name = get_item_names(qtree)

            if (exclude_volume and name == short_name) or (
                not exclude_volume and name == long_name
            ):
                yield Service(item=name)


def check_netapp_api_qtree_quota(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    qtree = section.get(item)
    if not qtree:
        return

    disk_limit = qtree.disk_limit
    if not disk_limit.isdigit():
        yield Result(state=State.UNKNOWN, summary="Qtree has no disk limit set")
        return

    size_total = int(disk_limit) / 1024.0
    size_avail = size_total - int(qtree.disk_used) / 1024.0
    if qtree.files_used.isdigit() and qtree.file_limit.isdigit():
        inodes_total = int(qtree.file_limit)
        inodes_avail = inodes_total - int(qtree.files_used)
    else:
        inodes_total = None
        inodes_avail = None

    yield from df.df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        size_mb=size_total,
        avail_mb=size_avail,
        reserved_mb=0,
        inodes_total=inodes_total,
        inodes_avail=inodes_avail,
        params=params,
    )


register.agent_section(name="netapp_api_qtree_quota", parse_function=parse_netapp_api_qtree_quota)

register.check_plugin(
    name="netapp_api_qtree_quota",
    service_name="Qtree %s",
    discovery_function=discover_netapp_api_qtree_quota,
    discovery_ruleset_name="discovery_qtree",
    discovery_default_parameters={"exclude_volume": False},
    check_function=check_netapp_api_qtree_quota,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_LEVELS,
)
