#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import MutableMapping
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_value_store,
    NoLevelsT,
    Service,
)

from .lib import SectionPodmanContainerInspect


class Params(TypedDict):
    restarts_total: NoLevelsT | FixedLevelsT[int]
    restarts_last_hour: NoLevelsT | FixedLevelsT[int]


def discover_podman_container_restarts(
    section: SectionPodmanContainerInspect,
) -> DiscoveryResult:
    yield Service()


def _calculate_restarts_last_hour(
    restarts: int,
    curr_timestamp_seconds: float,
    host_value_store: MutableMapping[str, Any],
) -> int | None:
    restart_count_list = host_value_store.setdefault("restart_count_list", [])

    cutoff_time = curr_timestamp_seconds - 3600
    restart_count_list[:] = [(ts, count) for ts, count in restart_count_list if ts >= cutoff_time]

    restart_count_list.append((curr_timestamp_seconds, restarts))

    return restarts - restart_count_list[0][1] if len(restart_count_list) > 1 else None


def _check_podman_container_restarts(
    params: Params,
    section: SectionPodmanContainerInspect,
    curr_timestamp_seconds: float,
    host_value_store: MutableMapping[str, Any],
) -> CheckResult:
    yield from check_levels(
        value=section.restarts,
        levels_upper=params.get("restarts_total"),
        label="Total",
        render_func=str,
        metric_name="podman_container_restarts_total",
    )

    restarts_last_hour = _calculate_restarts_last_hour(
        section.restarts,
        curr_timestamp_seconds,
        host_value_store,
    )
    if restarts_last_hour is not None:
        yield from check_levels(
            value=restarts_last_hour,
            levels_upper=params.get("restarts_last_hour"),
            label="In last hour",
            render_func=str,
            metric_name="podman_container_restarts_last_hour",
        )


def check_podman_container_restarts(
    params: Params,
    section: SectionPodmanContainerInspect,
) -> CheckResult:
    yield from _check_podman_container_restarts(
        params,
        section,
        time.time(),
        get_value_store(),
    )


check_plugin_podman_container_restarts = CheckPlugin(
    name="podman_container_restarts",
    service_name="Restarts",
    sections=["podman_container_inspect"],
    discovery_function=discover_podman_container_restarts,
    check_function=check_podman_container_restarts,
    check_ruleset_name="podman_container_restarts",
    check_default_parameters={},
)
