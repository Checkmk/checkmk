#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import IgnoreResultsError, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

# <<<oracle_crs_res:sep(124)>>>
# oracle_host|NAME=ora.DG_CLUSTER.dg
# oracle_host|TYPE=ora.diskgroup.type
# oracle_host|STATE=ONLINE on oracle_host
# oracle_host|TARGET=ONLINE
# oracle_host|NAME=ora.I31_ARCH.dg
# oracle_host|TYPE=ora.diskgroup.type
# oracle_host|STATE=ONLINE on oracle_host
# oracle_host|TARGET=ONLINE
# oracle_host|NAME=ora.I31_DATA.dg
# oracle_host|TYPE=ora.diskgroup.type
# oracle_host|STATE=ONLINE on oracle_host
# oracle_host|TARGET=ONLINE
# oracle_host|NAME=ora.I31_MLOG.dg
# oracle_host|TYPE=ora.diskgroup.type
# oracle_host|STATE=ONLINE on oracle_host
# oracle_host|TARGET=ONLINE
# ...usw...


@dataclass(frozen=True)
class Resource:
    type: str
    state: str
    target: str


@dataclass(frozen=True)
class Section:
    crs_nodename: Optional[str]
    resources: Mapping[str, Mapping[Optional[str], Resource]]


def parse(string_table: StringTable) -> Section:
    crs_nodename = None
    raw_ressources: dict[str, Any] = defaultdict(dict)
    entry: dict[str, str] = {}

    for line in string_table:
        if len(line) == 1:
            # Seems to be an old version where first column is missing:
            # <<<oracle_crs_res>>>
            # NAME=foo
            # TYPE=bar
            # STATE=baz
            nodename, varsetting = None, line[0]
        else:
            nodename, varsetting = line

        if nodename == "nodename":
            crs_nodename = varsetting
            continue

        key, value = varsetting.split("=", 1)
        if key == "NAME":
            res_name = value
            entry = {}
            raw_ressources.setdefault(res_name, {})
            raw_ressources[res_name][nodename] = entry
        else:
            entry[key.lower()] = value

    resources: dict[str, Mapping[Optional[str], Resource]] = {}
    for resname, values in raw_ressources.items():
        resources[resname] = {node: Resource(**entry) for node, entry in values.items()}
    return Section(crs_nodename, resources)


register.agent_section(name="oracle_crs_res", parse_function=parse)


def discover(section: Section) -> DiscoveryResult:
    for item in section.resources:
        yield Service(item=item)


def check(item: str, section: Section) -> CheckResult:
    if item not in section.resources:
        if item == "ora.cssd":
            yield Result(state=State.CRIT, summary="Clusterware not running")
        elif item == "ora.crsd":
            yield Result(state=State.CRIT, summary="Cluster resource service daemon not running")
        else:
            raise IgnoreResultsError(
                f"No resource details found for {item}, Maybe cssd/crsd is not running"
            )
        return
    for nodename, entry in section.resources[item].items():
        resstate = entry.state.split(" ", 1)[0]
        restarget = entry.target

        if nodename == "csslocal":
            infotext = "local: "
        elif nodename:
            infotext = "on " + nodename + ": "
        else:
            infotext = ""
        infotext += resstate.lower()

        if resstate != restarget:
            state = State.CRIT
            infotext += ", target state %s" % restarget.lower()
        else:
            state = State.OK
        yield Result(state=state, summary=infotext)


register.check_plugin(
    name="oracle_crs_res",
    service_name="ORA-GI %s Resource",
    discovery_function=discover,
    check_function=check,
)
