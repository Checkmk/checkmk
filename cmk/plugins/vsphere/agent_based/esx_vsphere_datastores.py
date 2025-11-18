#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections import defaultdict
from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

from cmk.agent_based.v1 import (
    check_levels as check_levels_v1,  # we can only use v2 after migrating the ruleset!
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

# Example output from agent:
# [zmucvm99-lds]
# accessible  True
# capacity    578478407680
# freeSpace   388398841856
# type    VMFS
# uncommitted 51973812224
# url /vmfs/volumes/513df1e9-12fd7366-ac5a-e41f13e69eaa


class Store(TypedDict):
    accessible: NotRequired[bool]
    capacity: NotRequired[int]
    freeSpace: NotRequired[int]
    uncommitted: NotRequired[int]


type Section = Mapping[str, Store]


def parse_esx_vsphere_datastores(string_table: StringTable) -> Section:
    stores: dict[str, Store] = defaultdict(Store)
    name = ""
    for line in string_table:
        if line[0].startswith("["):
            name = line[0][1:-1]
            continue

        match line:
            case "accessible" as key, value:
                stores[name][key] = value.lower() == "true"
            case "capacity" | "freeSpace" | "uncommitted" as key, value:
                stores[name][key] = int(value)
            case _:
                pass

    return stores


def check_esx_vsphere_datastores(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    if not data["accessible"]:
        yield Result(state=State.CRIT, summary="inaccessible")

    mib = 1024.0**2
    size_bytes = data.get("capacity")
    avail_bytes = data.get("freeSpace")
    if not size_bytes or avail_bytes is None:
        return

    yield from df_check_filesystem_single(
        get_value_store(), item, size_bytes / mib, avail_bytes / mib, 0, None, None, params
    )

    uncommitted_bytes = data.get("uncommitted")
    if not isinstance(uncommitted_bytes, int):
        return

    yield Result(state=State.OK, summary=f"Uncommitted: {render.bytes(uncommitted_bytes)}")
    yield Metric("uncommitted", uncommitted_bytes / mib)

    used_bytes = size_bytes - avail_bytes
    prov_bytes = used_bytes + uncommitted_bytes
    prov_percent = (prov_bytes * 100.0) / size_bytes if size_bytes != 0 else 0

    warn, crit = params.get("provisioning_levels", (None, None))
    yield from check_levels_v1(
        prov_percent,
        levels_upper=(warn, crit),
        render_func=render.percent,
        label="Provisioning",
    )

    if prov_bytes > size_bytes:
        prov_used = used_bytes / prov_bytes * 100.0
        yield Result(state=State.OK, summary=f"{render.percent(prov_used)} provisioned space used")

    if warn is not None:
        # convert percent to abs MiB
        scale = (size_bytes / mib) / 100.0
        yield Metric("overprovisioned", prov_bytes / mib, levels=(scale * warn, scale * crit))
    else:
        yield Metric("overprovisioned", prov_bytes / mib)


def discover_esx_vsphere_datastores(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_esx_vsphere_datastores = AgentSection(
    name="esx_vsphere_datastores",
    parse_function=parse_esx_vsphere_datastores,
)


check_plugin_esx_vsphere_datastores = CheckPlugin(
    name="esx_vsphere_datastores",
    service_name="Filesystem %s",
    discovery_function=discover_esx_vsphere_datastores,
    check_function=check_esx_vsphere_datastores,
    check_ruleset_name="esx_vsphere_datastores",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
