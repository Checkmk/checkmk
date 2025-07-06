#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-

# from cmk.base.check_legacy_includes.df import *
# from cmk.base.check_legacy_includes.size_trend import *

from collections.abc import Mapping
from typing import Any, Dict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    get_value_store,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS, df_check_filesystem_single
from cmk.plugins.hyperv.lib import parse_hyperv

Section = Dict[str, Mapping[str, Any]]


def discovery_hyperv_vm_vhd(section) -> DiscoveryResult:
    for key, values in section.items():
        if "vhd.path" in values:
            yield Service(item=key)


def check_hyperv_vm_vhd(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:

    value_store = get_value_store()
    disk_types = {
        "Differencing": (0, "Differencing disk size"),
        "Dynamic": (0, "Dynamic disk size"),
        "Fixed": (0, "Fixed disk size"),
        "Unknown": (3, "Disk type not found"),
    }

    data = section.get(item)

    if not data:
        yield Result(state=State(3), summary="Drive information is missing")
        return
    else:
        disk_type = data.get("vhd.type", "Unknown")

        disk_status, disk_txt = disk_types.get(disk_type, (3, "Disk type not found"))
        yield Result(state=State(disk_status), summary=disk_txt)

        capacity = float(data.get("vhd.maximumcapacity", "0.0").replace(",", ".")) * 1.0
        used_space = float(data.get("vhd.usedcapacity", "0.0").replace(",", ".")) * 1.0
        avail_mb = capacity - used_space

        yield from df_check_filesystem_single(
            value_store, item, capacity, avail_mb, 0, None, None, params=params
        )


agent_section_hyperv_vm_vhd = AgentSection(
    name="hyperv_vm_vhd",
    parse_function=parse_hyperv,
)

check_plugin_hyperv_vm_vhd = CheckPlugin(
    name="hyperv_vm_vhd",
    service_name="HyperV VHD %s",
    sections=["hyperv_vm_vhd"],
    discovery_function=discovery_hyperv_vm_vhd,
    check_function=check_hyperv_vm_vhd,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
