#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Prometheus Build Check"""

import json
from typing import Dict, Any, Optional
from .agent_based_api.v1 import Result, register, type_defs, State as state, Service

from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
)

Section = Dict[str, Any]


def parse_prometheus_build(string_table: type_defs.StringTable) -> Optional[Section]:
    section = {}
    try:
        prometheus_section = json.loads(string_table[0][0])
        section.update(prometheus_section)
    except ValueError:
        pass
    return section if section else None


register.agent_section(
    name="prometheus_build",
    parse_function=parse_prometheus_build,
)


def discovery_prometheus_build(section: Section) -> DiscoveryResult:
    yield Service()


def check_prometheus_build(section: Section) -> CheckResult:
    if "version" in section:
        # Only from Prometheus 2.14 the buildinfo endpoint is available which will show the version
        # number of the main Prometheus instance. For < 2.14 the version information can only be
        # retrieved via PromQl. However, the query returns the version of all connected instances
        # with no label to identify the main instance
        if len(section["version"]) == 1:
            version_summary = version_details = f"Version: {section['version'][0]}"
        else:
            version_summary = "Version: multiple instances"
            version_details = f"Versions: {', '.join(section['version'])}"
        yield Result(
            state=state.OK,
            summary=version_summary,
            details=version_details,
        )

    if "reload_config_status" in section:
        successful_reload = section["reload_config_status"]
        if successful_reload:
            reload_message = "Success"
            status = state.OK
        else:
            reload_message = "Failure"
            status = state.CRIT

        yield Result(
            state=status,
            summary=f"Config reload: {reload_message}",
        )

    if "storage_retention" in section:
        yield Result(
            state=state.OK,
            summary=f"Storage retention: {section['storage_retention']}",
        )

    if "scrape_target" in section:
        scrape_targets_info = section["scrape_target"]
        total_number = scrape_targets_info["targets_number"]
        down_targets = scrape_targets_info.get("down_targets", [])
        up_number = total_number - len(down_targets)

        if len(down_targets):
            down_target_names = f" (Targets in down state: {', '.join(down_targets)})"
            status = state.WARN
        else:
            status = state.OK
            down_target_names = ""

        summary = f"Scrape Targets in up state: {up_number} out of {total_number}"
        yield Result(
            state=status,
            summary=summary,
            details=f"{summary}{down_target_names}",
        )


register.check_plugin(
    name="prometheus_build",
    service_name="Prometheus Build",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_function=discovery_prometheus_build,
    check_function=check_prometheus_build,
)
