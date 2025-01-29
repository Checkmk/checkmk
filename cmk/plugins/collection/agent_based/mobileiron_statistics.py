#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Provides summarized insights into the fetched partitions.
Single service per mobileiron source host.
"""

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.mobileiron import SourceHostSection


def check_mobileiron_sourcehost(
    params: Mapping[str, Any], section: SourceHostSection
) -> CheckResult:
    yield Metric(
        name="mobileiron_devices_total",
        value=section.total_count,
    )

    yield Metric(name="mobileiron_non_compliant", value=section.non_compliant)

    non_compliant_percent = section.non_compliant / section.total_count * 100
    yield from check_levels_v1(
        label="Non-compliant devices",
        value=non_compliant_percent,
        metric_name="mobileiron_non_compliant_summary",
        levels_upper=params.get("non_compliant_summary_levels"),
        render_func=render.percent,
        notice_only=True,
        boundaries=(0, 100),
    )

    yield Result(
        state=State.OK,
        summary=f"Non-compliant: {section.non_compliant}",
    )

    yield Result(
        state=State.OK,
        summary=f"Total: {section.total_count}",
    )


def discover_single(section: SourceHostSection) -> DiscoveryResult:
    yield Service()


check_plugin_mobileiron_statistics = CheckPlugin(
    name="mobileiron_statistics",
    service_name="Mobileiron source host statistics",
    discovery_function=discover_single,
    check_function=check_mobileiron_sourcehost,
    check_ruleset_name="mobileiron_statistics",
    check_default_parameters={"non_compliant_summary_levels": (10.0, 20.0)},
)
