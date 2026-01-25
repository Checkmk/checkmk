#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

from .health import check_hp_msa_health, discover_hp_msa_health

# <<<hp_msa_volume>>>
# volumes 1 durable-id V0
# volumes 1 virtual-disk-name IMSAKO2B1_U1_B01-04
# volumes 1 storage-pool-name IMSAKO2B1_U1_B01-04
# volumes 1 volume-name IMSAKO2B1_U1_B01-04_v0001
# volumes 1 size 1198.9GB
# volumes 1 size-numeric 2341789696
# volumes 1 total-size 1198.9GB
# volumes 1 total-size-numeric 2341789696
# volumes 1 allocated-size 1198.9GB
# volumes 1 allocated-size-numeric 2341789696
# volumes 1 storage-type Linear
# volumes 1 storage-type-numeric 0
# volumes 1 preferred-owner A
# volumes 1 preferred-owner-numeric 1
# volumes 1 owner A
# volumes 1 owner-numeric 1
# volumes 1 serial-number 00c0ff1ec44a00008425415501000000
# volumes 1 write-policy write-back
# volumes 1 write-policy-numeric 1
# volumes 1 cache-optimization standard
# volumes 1 cache-optimization-numeric 0
# volumes 1 read-ahead-size Adaptive
# volumes 1 read-ahead-size-numeric -1
# volumes 1 volume-type standard
# volumes 1 volume-type-numeric 0
# volumes 1 volume-class standard
# volumes 1 volume-class-numeric 0
# volumes 1 profile-preference Standard
# volumes 1 profile-preference-numeric 0
# volumes 1 snapshot No
# volumes 1 volume-qualifier N/A
# volumes 1 volume-qualifier-numeric 0
# volumes 1 blocks 2341789696
# volumes 1 capabilities dmscer
# volumes 1 volume-parent
# volumes 1 snap-pool
# volumes 1 replication-set
# volumes 1 attributes
# volumes 1 virtual-disk-serial 00c0ff1ec44a00001e23415500000000
# volumes 1 volume-description
# volumes 1 wwn 600C0FF0001EC44A8425415501000000
# volumes 1 progress 0%
# volumes 1 progress-numeric 0
# volumes 1 container-name IMSAKO2B1_U1_B01-04
# volumes 1 container-serial 00c0ff1ec44a00001e23415500000000
# volumes 1 allowed-storage-tiers N/A
# volumes 1 allowed-storage-tiers-numeric 0
# volumes 1 threshold-percent-of-pool 0
# volumes 1 reserved-size-in-pages 0
# volumes 1 allocate-reserved-pages-first Disabled
# volumes 1 allocate-reserved-pages-first-numeric 0
# volumes 1 zero-init-page-on-allocation Disabled
# volumes 1 zero-init-page-on-allocation-numeric 0
# volumes 1 raidtype RAID10
# volumes 1 raidtype-numeric 10
# volumes 1 pi-format T0
# volumes 1 pi-format-numeric 0
# volumes 1 health OK
# volumes 1 health-numeric 0
# volumes 1 health-reason
# volumes 1 health-recommendation
# volumes 1 volume-group UNGROUPEDVOLUMES
# volumes 1 group-key VGU
# volume-statistics 1 volume-name IMSAKO2B1_U1_B01-04_v0001
# volume-statistics 1 serial-number 00c0ff1ec44a00008425415501000000
# volume-statistics 1 bytes-per-second 2724.3KB
# volume-statistics 1 bytes-per-second-numeric 2724352
# volume-statistics 1 iops 66
# volume-statistics 1 number-of-reads 11965055
# volume-statistics 1 number-of-writes 80032996
# volume-statistics 1 data-read 1241.3GB
# volume-statistics 1 data-read-numeric 1241361379840
# volume-statistics 1 data-written 6462.6GB
# volume-statistics 1 data-written-numeric 6462660316672
# volume-statistics 1 allocated-pages 0
# volume-statistics 1 percent-tier-ssd 0
# volume-statistics 1 percent-tier-sas 0
# volume-statistics 1 percent-tier-sata 0
# volume-statistics 1 percent-allocated-rfc 0
# volume-statistics 1 pages-alloc-per-minute 0
# volume-statistics 1 pages-dealloc-per-minute 0
# volume-statistics 1 shared-pages 0
# volume-statistics 1 write-cache-hits 93581599
# volume-statistics 1 write-cache-misses 345571865
# volume-statistics 1 read-cache-hits 29276023
# volume-statistics 1 read-cache-misses 54728207
# volume-statistics 1 small-destages 36593447
# volume-statistics 1 full-stripe-write-destages 4663277
# volume-statistics 1 read-ahead-operations 4804068203594569116
# volume-statistics 1 write-cache-space 74
# volume-statistics 1 write-cache-percent 8
# volume-statistics 1 reset-time 2015-05-22 13:54:36
# volume-statistics 1 reset-time-numeric 1432302876
# volume-statistics 1 start-sample-time 2015-08-21 11:51:17
# volume-statistics 1 start-sample-time-numeric 1440157877
# volume-statistics 1 stop-sample-time 2015-08-21 11:51:48
# volume-statistics 1 stop-sample-time-numeric 1440157908

#   .--health--------------------------------------------------------------.
#   |                    _                _ _   _                          |
#   |                   | |__   ___  __ _| | |_| |__                       |
#   |                   | '_ \ / _ \/ _` | | __| '_ \                      |
#   |                   | | | |  __/ (_| | | |_| | | |                     |
#   |                   |_| |_|\___|\__,_|_|\__|_| |_|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                            main check                                |
#   '----------------------------------------------------------------------'


Section = Mapping[str, Mapping[str, str]]


def _get_item_data(item: str, parsed: Section) -> Section:
    # ensure backward compatibility: get data in case either item is
    # "durable-id" (old) or item is "volume-name" (new)
    for k, v in parsed.items():
        if item in [k, v["durable-id"]]:
            return {item: v}
    return {}


def check_hp_msa_volume_health(item: str, section: Section) -> CheckResult:
    yield from check_hp_msa_health(item, _get_item_data(item, section))


def parse_hp_msa_volume(string_table: StringTable) -> Section:
    # use numerical id (2nd row from left) as uid for items,
    # in case of several values the values are whitespace separated as usual
    item_type_idx = 0
    numerical_id_idx = 1
    key_idx = 2
    value_idx = 3
    min_list_elements_cnt_with_values = 4
    pre_parsed: dict[str, dict[str, str]] = {}

    for line in string_table:
        if len(line) < min_list_elements_cnt_with_values:
            # make parsing robust against too short lists
            continue
        item_type = line[item_type_idx]
        numerical_id = line[numerical_id_idx]
        key = line[key_idx]
        values = " ".join(line[value_idx:])
        pre_parsed.setdefault(numerical_id, {}).setdefault(key, values)
        # set item type for lists with "volumes" in first element only
        # which is the case in case the 3rd element is "durable-id"
        if key == "durable-id":
            pre_parsed.setdefault(numerical_id, {}).setdefault("item_type", item_type)

    # replace numerical id with volume-name as uid for items, convert data
    parsed: dict[str, dict[str, str]] = {}
    for v in pre_parsed.values():
        parsed.setdefault(v["volume-name"], v)

    return parsed


agent_section_hp_msa_volume = AgentSection(
    name="hp_msa_volume",
    parse_function=parse_hp_msa_volume,
)


check_plugin_hp_msa_volume = CheckPlugin(
    name="hp_msa_volume",
    service_name="Volume Health %s",
    discovery_function=discover_hp_msa_health,
    check_function=check_hp_msa_volume_health,
)

# .
#   .--volume df-----------------------------------------------------------.
#   |                       _                            _  __             |
#   |           __   _____ | |_   _ _ __ ___   ___    __| |/ _|            |
#   |           \ \ / / _ \| | | | | '_ ` _ \ / _ \  / _` | |_             |
#   |            \ V / (_) | | |_| | | | | | |  __/ | (_| |  _|            |
#   |             \_/ \___/|_|\__,_|_| |_| |_|\___|  \__,_|_|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_hp_msa_volume_df(section: Section) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_hp_msa_volume_df(
    item: str, params: Mapping[str, object], section: Section
) -> CheckResult:
    yield from check_hp_msa_volume_df_testable(
        item, params, section, get_value_store(), time.time()
    )


def check_hp_msa_volume_df_testable(
    item: str,
    params: Mapping[str, object],
    section: Section,
    value_store: MutableMapping[str, Any],
    this_time: float,
) -> CheckResult:
    parsed = _get_item_data(item, section)
    if item not in parsed:
        return

    yield Result(
        state=State.OK,
        summary="{} ({})".format(parsed[item]["virtual-disk-name"], parsed[item]["raidtype"]),
    )

    size_mb = (int(parsed[item]["total-size-numeric"]) * 512) // 1024**2
    alloc_mb = (int(parsed[item]["allocated-size-numeric"]) * 512) // 1024**2
    avail_mb = size_mb - alloc_mb

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=size_mb,
        free_space=avail_mb,
        reserved_space=0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
        this_time=this_time,
    )


check_plugin_hp_msa_volume_df = CheckPlugin(
    name="hp_msa_volume_df",
    service_name="Filesystem %s",
    sections=["hp_msa_volume"],
    discovery_function=discover_hp_msa_volume_df,
    check_function=check_hp_msa_volume_df,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
