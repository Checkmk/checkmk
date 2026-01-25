#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

# .1.3.6.1.4.1.110901.1.2.1.1.1.2.1       lib status
# .1.3.6.1.4.1.110901.1.2.2.1.1.8.1.1.x   drive x status
# .1.3.6.1.4.1.110901.1.3.1.1.4.1         actor status

# .1.3.6.1.4.1.110901.1.4.1.0             archive status
# .1.3.6.1.4.1.110901.1.4.2.0             archive objects count
# .1.3.6.1.4.1.110901.1.4.3.0             blank tapes count
# .1.3.6.1.4.1.110901.1.4.4.0             remaining size on tapes
# .1.3.6.1.4.1.110901.1.4.5.0             total size on tapes

#
# Note: These checks was designed a bit atypically (for no good reason):
#   The drive, actor, archive, tapes and library checks are subchecks of the status
#   check although none of these checks share the same oids.
#   As a result, "info" is always a list of 6 sublists and each check only
#   accesses exactly one of the sublists.
#

# .
#   .--Status--------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ __ _| |_ _   _ ___                      |
#   |                   \___ \| __/ _` | __| | | / __|                     |
#   |                    ___) | || (_| | |_| |_| \__ \                     |
#   |                   |____/ \__\__,_|\__|\__,_|___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    LevelsT,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def item_name_oracle_diva_csm(name: str, element_id: str) -> str:
    return (f"{name} {element_id}").strip()


def inventory_oracle_diva_csm_status(
    name: str, idx: int, info: Sequence[StringTable]
) -> DiscoveryResult:
    for line in info[idx]:
        if len(line) == 2:
            element_id, _reading = line
        else:
            element_id = ""

        yield Service(item=item_name_oracle_diva_csm(name, element_id), parameters=None)


def status_result_oracle_diva_csm(reading: str) -> tuple[int, str]:
    if reading == "1":
        return 0, "online"
    if reading == "2":
        return 2, "offline"
    if reading == "3":
        return 1, "unknown"
    return 3, "unexpected state"


def check_oracle_diva_csm_status(
    name: str, idx: int, item: str, params: Mapping[str, Any], info: Sequence[StringTable]
) -> CheckResult:
    for line in info[idx]:
        if len(line) == 2:
            element_id, reading = line
        else:
            element_id = ""
            reading = line[0]

        if item_name_oracle_diva_csm(name, element_id) == item:
            state, summary = status_result_oracle_diva_csm(reading)
            yield Result(state=State(state), summary=summary)
            return
    return None


def parse_oracle_diva_csm(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


def discover_oracle_diva_csm(section: Sequence[StringTable]) -> DiscoveryResult:
    yield from inventory_oracle_diva_csm_status("Library", 0, section)


def check_oracle_diva_csm(
    item: str, params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    yield from check_oracle_diva_csm_status("Library", 0, item, params, section)


snmp_section_oracle_diva_csm = SNMPSection(
    name="oracle_diva_csm",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311.1.1.3.1.2"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.110901.1.2.1.1.1",
            oids=["1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.110901.1.2.2.1.1",
            oids=["3", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.110901.1.3.1.1",
            oids=["2", "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.110901.1.4",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.110901.1.4",
            oids=["2", "4", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.110901.1.4",
            oids=["3"],
        ),
    ],
    parse_function=parse_oracle_diva_csm,
)


check_plugin_oracle_diva_csm = CheckPlugin(
    name="oracle_diva_csm",
    service_name="DIVA Status %s",
    discovery_function=discover_oracle_diva_csm,
    check_function=check_oracle_diva_csm,
    check_default_parameters={},
)


def discover_oracle_diva_csm_drive(section: Sequence[StringTable]) -> DiscoveryResult:
    yield from inventory_oracle_diva_csm_status("Drive", 1, section)


def check_oracle_diva_csm_drive(
    item: str, params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    yield from check_oracle_diva_csm_status("Drive", 1, item, params, section)


check_plugin_oracle_diva_csm_drive = CheckPlugin(
    name="oracle_diva_csm_drive",
    service_name="DIVA Status %s",
    sections=["oracle_diva_csm"],
    discovery_function=discover_oracle_diva_csm_drive,
    check_function=check_oracle_diva_csm_drive,
    check_default_parameters={},
)


def discover_oracle_diva_csm_actor(section: Sequence[StringTable]) -> DiscoveryResult:
    yield from inventory_oracle_diva_csm_status("Actor", 2, section)


def check_oracle_diva_csm_actor(
    item: str, params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    yield from check_oracle_diva_csm_status("Actor", 2, item, params, section)


check_plugin_oracle_diva_csm_actor = CheckPlugin(
    name="oracle_diva_csm_actor",
    service_name="DIVA Status %s",
    sections=["oracle_diva_csm"],
    discovery_function=discover_oracle_diva_csm_actor,
    check_function=check_oracle_diva_csm_actor,
    check_default_parameters={},
)


def discover_oracle_diva_csm_archive(section: Sequence[StringTable]) -> DiscoveryResult:
    yield from inventory_oracle_diva_csm_status("Manager", 3, section)


def check_oracle_diva_csm_archive(
    item: str, params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    yield from check_oracle_diva_csm_status("Manager", 3, item, params, section)


check_plugin_oracle_diva_csm_archive = CheckPlugin(
    name="oracle_diva_csm_archive",
    service_name="DIVA Status %s",
    sections=["oracle_diva_csm"],
    discovery_function=discover_oracle_diva_csm_archive,
    check_function=check_oracle_diva_csm_archive,
    check_default_parameters={},
)

# .
#   .--Managed Objects-----------------------------------------------------.
#   |              __  __                                  _               |
#   |             |  \/  | __ _ _ __   __ _  __ _  ___  __| |              |
#   |             | |\/| |/ _` | '_ \ / _` |/ _` |/ _ \/ _` |              |
#   |             | |  | | (_| | | | | (_| | (_| |  __/ (_| |              |
#   |             |_|  |_|\__,_|_| |_|\__,_|\__, |\___|\__,_|              |
#   |                                       |___/                          |
#   |                    ___  _     _           _                          |
#   |                   / _ \| |__ (_) ___  ___| |_ ___                    |
#   |                  | | | | '_ \| |/ _ \/ __| __/ __|                   |
#   |                  | |_| | |_) | |  __/ (__| |_\__ \                   |
#   |                   \___/|_.__// |\___|\___|\__|___/                   |
#   |                            |__/                                      |
#   '----------------------------------------------------------------------'


def discover_oracle_diva_csm_objects(section: Sequence[StringTable]) -> DiscoveryResult:
    if len(section) > 4 and len(section[4]) > 0:
        yield Service()


def check_oracle_diva_csm_objects(section: Sequence[StringTable]) -> CheckResult:
    GB = 1024 * 1024 * 1024
    if len(section) > 4 and len(section[4]) > 0:
        object_count, remaining_size, total_size = map(int, section[4][0])

        infotext = f"managed objects: {object_count}, remaining size: {remaining_size} GB of {total_size} GB"

        yield Result(state=State.OK, summary=infotext)
        yield Metric("managed_object_count", object_count)
        yield Metric(
            "storage_used",
            (total_size - remaining_size) * GB,
            boundaries=(
                0,
                total_size * GB,
            ),
        )
        return
    return None


check_plugin_oracle_diva_csm_objects = CheckPlugin(
    name="oracle_diva_csm_objects",
    service_name="DIVA Managed Objects",
    sections=["oracle_diva_csm"],
    discovery_function=discover_oracle_diva_csm_objects,
    check_function=check_oracle_diva_csm_objects,
)

# .
#   .--Tapes---------------------------------------------------------------.
#   |                      _____                                           |
#   |                     |_   _|_ _ _ __   ___  ___                       |
#   |                       | |/ _` | '_ \ / _ \/ __|                      |
#   |                       | | (_| | |_) |  __/\__ \                      |
#   |                       |_|\__,_| .__/ \___||___/                      |
#   |                               |_|                                    |
#   '----------------------------------------------------------------------'


def discover_oracle_diva_csm_tapes(section: Sequence[StringTable]) -> DiscoveryResult:
    if len(section) > 5 and len(section[5]) > 0 and len(section[5][0]) > 0:
        yield Service()


def check_oracle_diva_csm_tapes(
    params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    try:
        blank_tapes = int(section[5][0][0])
    except IndexError:
        return

    match params["levels_lower"]:
        case None:
            levels_lower: LevelsT = ("no_levels", None)
        case (warn, crit):
            levels_lower = ("fixed", (warn, crit))

    yield from check_levels(
        blank_tapes,
        levels_lower=levels_lower,
        metric_name="tapes_free",
        render_func=str,
        label="Blank tapes",
    )


check_plugin_oracle_diva_csm_tapes = CheckPlugin(
    name="oracle_diva_csm_tapes",
    service_name="DIVA Blank Tapes",
    sections=["oracle_diva_csm"],
    discovery_function=discover_oracle_diva_csm_tapes,
    check_function=check_oracle_diva_csm_tapes,
    check_ruleset_name="blank_tapes",
    check_default_parameters={"levels_lower": (5, 1)},
)
