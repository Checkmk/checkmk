#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-
import time
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
from cmk.plugins.lib.diskstat import check_diskstat_dict
from cmk.plugins.hyperv.lib import parse_hyperv_io

Section = Dict[str, Mapping[str, Any]]


def discovery_hyperv_host_io_local(section: Section) -> DiscoveryResult:
    for lun in section.keys():
        yield Service(item=lun)


def check_hyperv_host_io_local(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:

    lun = section.get(item, "")

    if not lun:
        yield Result(state=State(3), summary="CSV not found in agent output")
        return

    disk = {
        "node": None,
        "read_ql": float(lun["avg. disk read queue length"].replace(",", ".")),
        "write_ql": float(lun["avg. disk write queue length"].replace(",", ".")),
        "sec_per_read_counter": float(lun["avg. disk sec/read"].replace(",", ".")),
        "sec_per_write_counter": float(lun["avg. disk sec/write"].replace(",", ".")),
        "read_ios": float(lun["disk reads/sec"].replace(",", ".")),
        "write_ios": float(lun["disk writes/sec"].replace(",", ".")),
        "read_throughput": float(lun["disk read bytes/sec"].replace(",", ".")),
        "write_throughput": float(lun["disk write bytes/sec"].replace(",", ".")),
    }
    yield from check_diskstat_dict(
        params=params,
        disk=disk,
        value_store=get_value_store(),
        this_time=time.time(),
    )


agent_section_hyperv_host_io_local = AgentSection(
    name="hyperv_host_io_local",
    parse_function=parse_hyperv_io,
)

check_plugin_hyperv_host_io_local = CheckPlugin(
    name="hyperv_host_io_local",
    service_name="HyperV IO Local %s",
    sections=["hyperv_host_io_local"],
    check_default_parameters={},
    discovery_function=discovery_hyperv_host_io_local,
    check_function=check_hyperv_host_io_local,
    check_ruleset_name="diskstat",
)
