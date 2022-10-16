#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import get_value_store, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_LEVELS

Section = Dict[str, Any]


def discovery_prism_host_usage(section: Section) -> DiscoveryResult:
    data = section.get("usage_stats", {})
    if data.get("storage.capacity_bytes"):
        yield Service(item="Capacity")


def check_prism_host_usage(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get("usage_stats")
    if not data:
        return

    value_store = get_value_store()
    total_sas = float(data.get("storage_tier.das-sata.capacity_bytes", 0))
    free_sas = float(data.get("storage_tier.das-sata.free_bytes", 0))
    total_ssd = float(data.get("storage_tier.ssd.capacity_bytes", 0))
    free_ssd = float(data.get("storage_tier.ssd.free_bytes", 0))
    total_bytes = float(data.get("storage.capacity_bytes", 0))
    free_bytes = float(data.get("storage.free_bytes", 0))

    yield from df_check_filesystem_single(
        value_store,
        item,
        total_bytes / 1024**2,
        free_bytes / 1024**2,
        0,
        None,
        None,
        params=params,
    )
    message = f"Total SAS: {render.bytes(total_sas)}, Free SAS: {render.bytes(free_sas)}"
    yield Result(state=State(0), summary=message)
    message = f"Total SSD: {render.bytes(total_ssd)}, Free SSD: {render.bytes(free_ssd)}"
    yield Result(state=State(0), summary=message)


register.check_plugin(
    name="prism_host_usage",
    service_name="NTNX Storage %s",
    sections=["prism_host"],
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
    discovery_function=discovery_prism_host_usage,
    check_function=check_prism_host_usage,
    check_ruleset_name="filesystem",
)
