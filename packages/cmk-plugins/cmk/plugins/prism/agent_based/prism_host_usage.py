#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from contextlib import suppress
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    GetRateError,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

Section = Mapping[str, Any]


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

    with suppress(GetRateError):
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


check_plugin_prism_host_usage = CheckPlugin(
    name="prism_host_usage",
    service_name="NTNX Storage %s",
    sections=["prism_host"],
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    discovery_function=discovery_prism_host_usage,
    check_function=check_prism_host_usage,
    check_ruleset_name="filesystem",
)
