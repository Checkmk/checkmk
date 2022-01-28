#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Mapping, Tuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    get_value_store,
    register,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils.k8s import PodContainers

ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE


def discovery(section: PodContainers) -> DiscoveryResult:
    yield Service()


def check(params: Mapping[str, Tuple[int, int]], section: PodContainers) -> CheckResult:
    restart_count = sum(container.restart_count for container in section.containers.values())
    yield from check_levels(
        restart_count,
        levels_upper=params.get("restart_count"),
        metric_name="kube_pod_restart_count",
        render_func=str,
        label="Total",
    )
    yield from check_levels(
        _calc_restart_rate_in_last_hour(restart_count),
        levels_upper=params.get("restart_rate"),
        metric_name="kube_pod_restart_rate",
        render_func=str,
        label="In last hour",
    )


def _calc_restart_rate_in_last_hour(restart_count: int) -> int:
    curr_timestamp_seconds = int(time.time())
    host_value_store = get_value_store()
    restart_count_list = host_value_store.setdefault("restart_count_list", [])
    while restart_count_list and restart_count_list[0][0] <= curr_timestamp_seconds - ONE_HOUR:
        restart_count_list.pop(0)
    restart_count_list.append((curr_timestamp_seconds, restart_count))
    if len(restart_count_list) > 1:
        return restart_count - restart_count_list[0][1]
    return restart_count


register.check_plugin(
    name="kube_pod_restarts",
    service_name="Restarts",
    sections=["kube_pod_containers"],
    discovery_function=discovery,
    check_function=check,
    check_default_parameters={},
    check_ruleset_name="kube_pod_restarts",
)
