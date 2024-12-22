#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any, TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    InventoryPlugin,
    InventoryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util_unix, CPUInfo


class Section(TypedDict, total=False):
    system_config: Mapping[str, str]
    update_required: bool
    cpu: Mapping[str, float]
    util: Mapping[str, tuple[float, str]]


def parse_lparstat_aix(string_table: StringTable) -> Section | None:
    if not string_table:
        return None

    if len(string_table) < 4:
        return {"update_required": True}

    # get system config:
    kv_pairs = (word for word in string_table[0] if "=" in word)
    system_config = dict(kv.split("=", 1) for kv in kv_pairs)
    # from ibm.com: 'If there are two SMT threads, the row is displayed as "on."'
    if system_config.get("smt", "").lower() == "on":
        system_config["smt"] = "2"

    cpu = {}
    util = {}
    for index, key in enumerate(string_table[1]):
        name = key.lstrip("%")
        uom = "%" if "%" in key else ""
        try:
            value = float(string_table[3][index])
        except (IndexError, ValueError):
            continue

        if name in ("user", "sys", "idle", "wait"):
            cpu[name] = value
        else:
            util[name] = (value, uom)

    return {
        "system_config": system_config,
        "util": util,
        "cpu": cpu,
    }


agent_section_lparstat_aix = AgentSection(
    name="lparstat_aix",
    parse_function=parse_lparstat_aix,
)


def inventory_lparstat_aix(section: Section) -> InventoryResult:
    data = section.get("system_config", {})
    attr = {}

    sharing_mode = "-".join(v for k in ("type", "mode") if (v := data.get(k)))
    if sharing_mode:
        attr["sharing_mode"] = sharing_mode

    for nkey, dkey in [
        ("smt_threads", "smt"),
        ("entitlement", "ent"),
        ("cpus", "psize"),
        ("logical_cpus", "lcpu"),
    ]:
        try:
            attr[nkey] = data[dkey]
        except KeyError:
            pass

    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes=attr,
    )


inventory_plugin_lparstat_aix = InventoryPlugin(
    name="lparstat_aix",
    inventory_function=inventory_lparstat_aix,
)


def discover_lparstat(section: Section) -> DiscoveryResult:
    if section.get("util"):
        yield Service()


def check_lparstat(section: Section) -> CheckResult:
    if section.get("update_required"):
        yield Result(state=State.UNKNOWN, summary="Please upgrade your AIX agent.")
        return

    utilization = section.get("util", {})
    for name, (value, uom) in utilization.items():
        yield Result(state=State.OK, summary=f"{name.title()}: {value}{uom}")
        yield Metric(name, value)


check_plugin_lparstat_aix = CheckPlugin(
    name="lparstat_aix",
    service_name="lparstat",
    discovery_function=discover_lparstat,
    check_function=check_lparstat,
)


def discover_lparstat_aix_cpu(section: Section) -> DiscoveryResult:
    if section.get("update_required") or set(section.get("cpu", ())) >= {
        "user",
        "sys",
        "wait",
        "idle",
    }:
        yield Service()


def check_lparstat_aix_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    if section.get("update_required"):
        yield Result(state=State.UNKNOWN, summary="Please upgrade your AIX agent.")
        return

    cpu = section.get("cpu", {})
    try:
        cpu_info = CPUInfo("", cpu["user"], 0, cpu["sys"], cpu.get("idle", 0), cpu["wait"])
    except KeyError:
        return

    yield from check_cpu_util_unix(
        cpu_info=cpu_info,
        params=params,
        this_time=time.time(),
        value_store=get_value_store(),
        cores=(),
        values_counter=False,
    )

    try:
        cpu_entitlement = float(section["system_config"]["ent"])
        phys_cpu_consumption, _unit = section["util"]["physc"]
    except (KeyError, ValueError):
        return
    yield from check_levels(
        phys_cpu_consumption,
        metric_name="cpu_entitlement_util",
        label="Physical CPU consumption",
        render_func=lambda v: f"{v} CPUs",
    )
    yield from check_levels(
        cpu_entitlement,
        metric_name="cpu_entitlement",
        label="Entitlement",
        render_func=lambda v: f"{v} CPUs",
    )


check_plugin_lparstat_aix_cpu_util = CheckPlugin(
    name="lparstat_aix_cpu_util",
    service_name="CPU utilization",
    sections=["lparstat_aix"],
    discovery_function=discover_lparstat_aix_cpu,
    check_function=check_lparstat_aix_cpu,
    check_ruleset_name="cpu_iowait",
    check_default_parameters={},
)
