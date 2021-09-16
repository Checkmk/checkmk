#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, Tuple

from .agent_based_api.v1 import get_value_store, OIDEnd, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.df import (
    df_check_filesystem_list,
    df_discovery,
    FILESYSTEM_DEFAULT_LEVELS,
    mountpoints_in_group,
)
from .utils.hitachi_hnas import DETECT, parse_physical_volumes, parse_virtual_volumes

STATE_MAP = {
    "mounted": State.OK,
    "unformatted": State.WARN,
    "formatted": State.WARN,
    "needsChecking": State.CRIT,
}


class Section(NamedTuple):
    volumes: Dict[str, Tuple[str, Optional[float], Optional[float], str]]
    virtual_volumes: Dict[str, Tuple[Optional[float], Optional[float]]]


def parse_hitachi_hnas_volume(string_table):
    volumes, virtual_volumes, quotas = string_table

    map_label, parsed_volumes = parse_physical_volumes(volumes)
    parsed_virtual_volumes = parse_virtual_volumes(map_label, virtual_volumes, quotas)

    return Section(volumes=parsed_volumes, virtual_volumes=parsed_virtual_volumes)


register.snmp_section(
    name="hitachi_hnas_volume",
    parse_function=parse_hitachi_hnas_volume,
    fetch=[
        SNMPTree(
            # BLUEARC-SERVER-MIB
            base=".1.3.6.1.4.1.11096.6.1.1.1.3.5.2.1",
            oids=[
                # volumeEntry
                "1",  # volumeSysDriveIndex
                "3",  # volumeLabel
                "4",  # volumeStatus
                "5",  # volumeCapacity
                "6",  # volumeFreeCapacity
                "7",  # volumeEnterpriseVirtualServer
            ],
        ),
        SNMPTree(
            # virtualVolumeTitanEntry
            base=".1.3.6.1.4.1.11096.6.2.1.2.1.2.1",
            oids=[
                # virtualVolumeTitanEntry
                OIDEnd(),  # needed for referencing between tables
                "1",  # virtualVolumeTitanSpanId
                "2",  # virtualVolumeTitanName
            ],
        ),
        SNMPTree(
            # BLUEARC-TITAN-MIB
            base=".1.3.6.1.4.1.11096.6.2.1.2.1.7.1",
            oids=[
                # virtualVolumeTitanQuotasEntry
                OIDEnd(),  # needed for referencing between tables
                "3",  # virtualVolumeTitanQuotasTargetType
                "4",  # virtualVolumeTitanQuotasUsage
                "5",  # virtualVolumeTitanQuotasUsageLimit
            ],
        ),
    ],
    detect=DETECT,
)

# .
#   .--Volume--------------------------------------------------------------.
#   |                __     __    _                                        |
#   |                \ \   / /__ | |_   _ _ __ ___   ___                   |
#   |                 \ \ / / _ \| | | | | '_ ` _ \ / _ \                  |
#   |                  \ V / (_) | | |_| | | | | | |  __/                  |
#   |                   \_/ \___/|_|\__,_|_| |_| |_|\___|                  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_hitachi_hnas_volume(
    params: List[Mapping[str, Any]],
    section: Section,
) -> DiscoveryResult:
    for service_name, param in df_discovery(params, list(section.volumes.keys())):
        yield Service(item=service_name, parameters=param)


def check_hitachi_hnas_volume(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:

    fslist_blocks = [
        (mount_point, size_mb, avail_mb, 0)
        for mount_point, (_, size_mb, avail_mb, _) in section.volumes.items()
    ]

    blocks_info = {
        mountp: {
            "size_mb": size_mb,
            "avail_mb": avail_mb,
            "reserved_mb": 0,
        }
        for mountp, (_, size_mb, avail_mb, _) in section.volumes.items()
    }

    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=fslist_blocks,
    )

    if "patterns" in params:
        matching_mountpoints = mountpoints_in_group(blocks_info, *params["patterns"])
    else:
        matching_mountpoints = [item]

    for mp in matching_mountpoints:
        status = section.volumes[mp][0]
        evs = section.volumes[mp][3]

        if status == "unidentified":
            yield Result(
                state=State.CRIT,
                summary="Volume reports unidentified status",
            )
        else:
            yield Result(
                state=STATE_MAP[status],
                summary=f"Status: {status}",
            )

        yield Result(
            state=State.OK,
            summary=f"assigned to EVS {evs}",
        )


register.check_plugin(
    name="hitachi_hnas_volume",
    service_name="Volumes %s",
    discovery_function=discovery_hitachi_hnas_volume,
    discovery_default_parameters={},
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_hitachi_hnas_volume,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
)

# .
#   .--Virt. Volume--------------------------------------------------------.
#   |     __     ___      _      __     __    _                            |
#   |     \ \   / (_)_ __| |_    \ \   / /__ | |_   _ _ __ ___   ___       |
#   |      \ \ / /| | '__| __|    \ \ / / _ \| | | | | '_ ` _ \ / _ \      |
#   |       \ V / | | |  | |_ _    \ V / (_) | | |_| | | | | | |  __/      |
#   |        \_/  |_|_|   \__(_)    \_/ \___/|_|\__,_|_| |_| |_|\___|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discovery_hitachi_hnas_virtual_volume(
    params: List[Mapping[str, Any]],
    section: Section,
) -> DiscoveryResult:
    for service_name, param in df_discovery(params, list(section.virtual_volumes.keys())):
        yield Service(item=service_name, parameters=param)


def check_hitachi_hnas_virtual_volume(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:

    fslist_blocks = [
        (mount_point, size_mb, avail_mb, 0)
        for mount_point, (size_mb, avail_mb) in section.virtual_volumes.items()
    ]

    blocks_info = {
        mountp: {
            "size_mb": size_mb,
            "avail_mb": avail_mb,
            "reserved_mb": 0,
        }
        for mountp, (size_mb, avail_mb) in section.virtual_volumes.items()
    }

    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=fslist_blocks,
    )

    if "patterns" in params:
        matching_mountpoints = mountpoints_in_group(blocks_info, *params["patterns"])
    else:
        matching_mountpoints = [item]

    for mp in matching_mountpoints:
        try:
            size_mb, avail_mb = section.virtual_volumes[mp]
        except KeyError:
            yield Result(
                state=State.OK,
                summary="no quota defined",
            )
            return

        if (size_mb is None) or (avail_mb is None):
            yield Result(state=State.OK, summary="no quota size information")


register.check_plugin(
    name="hitachi_hnas_volume_virtual",
    sections=["hitachi_hnas_volume"],
    service_name="Volumes %s",
    discovery_function=discovery_hitachi_hnas_virtual_volume,
    discovery_default_parameters={},
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_hitachi_hnas_virtual_volume,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
)
