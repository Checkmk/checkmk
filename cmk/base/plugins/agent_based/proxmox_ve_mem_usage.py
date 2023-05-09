#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping
import json

from cmk.base.plugins.agent_based.utils.memory import check_element
from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

Section = Mapping[str, float]


def parse_proxmox_ve_mem_usage(string_table: StringTable) -> Section:
    return {key: float(value) for key, value in json.loads(string_table[0][0]).items()}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_mem_usage(params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_mem_usage(
    ...     {"levels": (80., 90.)},
    ...     parse_proxmox_ve_mem_usage([['{"max_mem": 67424276480, "mem": 32768163840}']])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Usage: 48.60% - 30.5 GiB of 62.8 GiB')
    Metric('mem_used', 32768163840.0, levels=(53939421184.0, 60681848832.0), boundaries=(0.0, 67424276480.0))
    Metric('mem_used_percent', 48.59994878806002, levels=(80.0, 90.0), boundaries=(0.0, None))
    """
    yield from check_element(
        "Usage",
        float(section.get("mem", 0)),
        float(section.get("max_mem", 0)),
        ("perc_used", params["levels"]),
        metric_name="mem_used",
        create_percent_metric=True,
    )


register.agent_section(
    name="proxmox_ve_mem_usage",
    parse_function=parse_proxmox_ve_mem_usage,
)

register.check_plugin(
    name="proxmox_ve_mem_usage",
    service_name="Proxmox VE Memory Usage",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_mem_usage,
    check_ruleset_name="proxmox_ve_mem_usage",
    check_default_parameters={"levels": None},
)
