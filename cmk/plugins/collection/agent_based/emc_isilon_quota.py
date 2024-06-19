#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, df_discovery, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.emc import DETECT_ISILON


class IsilonQuota(NamedTuple):
    hard_threshold: int
    soft_threshold_defined: str
    soft_threshold: int
    advisory_threshold_defined: str
    advisory_threshold: int
    usage: int


Section = Mapping[str, IsilonQuota]


def parse_emc_isilon_quota(string_table: StringTable) -> Section:
    return {
        path: IsilonQuota(
            int(hard_threshold),  # can't be exceeded
            soft_threshold_defined,
            int(soft_threshold),  # write-protect after grace period
            advisory_threshold_defined,
            int(advisory_threshold),  # warning only
            int(usage),
        )
        for (
            path,
            hard_threshold,
            soft_threshold_defined,
            soft_threshold,
            advisory_threshold_defined,
            advisory_threshold,
            usage,
        ) in string_table
    }


snmp_section_emc_isilon_quota = SimpleSNMPSection(
    name="emc_isilon_quota",
    parse_function=parse_emc_isilon_quota,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.1.12.1.1",
        oids=[
            "5",  # quotaPath
            "7",  # quotaHardThreshold
            "8",  # quotaSoftThresholdDefined
            "9",  # quotaSoftThreshold
            "10",  # quotaAdvisoryThresholdDefined
            "11",  # quotaAdvisoryThreshold
            "13",  # quotaUsage
        ],
    ),
    detect=DETECT_ISILON,
)


def discover_emc_isilon_quota(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    yield from df_discovery(params, list(section))


def _percent_levels(value: float, total: float, fallback: float) -> float:
    return value * 100.0 / total if value else fallback


def check_emc_isilon_quota(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    byte_to_mb = float(1024 * 1024)

    fslist_blocks = []

    for path, quota in section.items():
        if "patterns" in params or item == path:
            # note 1: quota type is currently unused
            # note 2: even if quotaHardThresholdDefined is 0 the
            #         quotaHardThreshold is still often set to a reasonable value. Otherwise,
            #         use the "hardest" threshold that isn't 0 for the disk limit
            assumed_size = quota.hard_threshold or quota.soft_threshold or quota.advisory_threshold

            # If the users has not configured levels, we use the soft/advisory threshold
            if "levels" not in params and (
                quota.soft_threshold_defined == "1" or quota.advisory_threshold_defined == "1"
            ):
                params = {
                    "levels": (
                        # if a advisory threshold is set, it will be used as warning level
                        _percent_levels(quota.advisory_threshold, assumed_size, 80.0),
                        # if a soft threshold is set, it will be used as crit
                        # (since the hard_threshold can't be exceeded anyway)
                        _percent_levels(quota.soft_threshold, assumed_size, 90.0),
                    ),
                    **params,
                }

            avail = assumed_size - quota.usage
            fslist_blocks.append((path, assumed_size / byte_to_mb, avail / byte_to_mb, 0))

    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=fslist_blocks,
    )


check_plugin_emc_isilon_quota = CheckPlugin(
    name="emc_isilon_quota",
    service_name="Quota %s",
    discovery_function=discover_emc_isilon_quota,
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"groups": []},
    check_function=check_emc_isilon_quota,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
