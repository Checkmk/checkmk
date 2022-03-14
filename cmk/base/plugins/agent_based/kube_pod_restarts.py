#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Literal, MutableMapping, Optional, Tuple, TypedDict, Union

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


VSResultInteger = Union[Tuple[Literal["levels"], Tuple[int, int]], Literal["no_levels"]]


class Params(TypedDict):
    restart_count: VSResultInteger
    restart_rate: VSResultInteger


_DEFAULT_PARAMS = Params(restart_count="no_levels", restart_rate="no_levels")


def check_kube_pod_restarts(params: Params, section: PodContainers) -> CheckResult:
    yield from _check(params, section, int(time.time()), get_value_store())


def _check(
    params: Params,
    section: PodContainers,
    curr_timestamp_seconds: int,
    host_value_store: MutableMapping[str, Any],
) -> CheckResult:
    restart_count = sum(container.restart_count for container in section.containers.values())
    yield from check_levels(
        restart_count,
        levels_upper=params["restart_count"][1] if params["restart_count"] != "no_levels" else None,
        metric_name="kube_pod_restart_count",
        render_func=str,
        label="Total",
    )
    restart_rate = _calc_restart_rate_in_last_hour(
        restart_count,
        curr_timestamp_seconds,
        host_value_store,
    )
    if restart_rate is not None:
        yield from check_levels(
            restart_rate,
            levels_upper=params["restart_rate"][1]
            if params["restart_rate"] != "no_levels"
            else None,
            metric_name="kube_pod_restart_rate",
            render_func=str,
            label="In last hour",
        )


def _calc_restart_rate_in_last_hour(
    restart_count: int,
    curr_timestamp_seconds: int,
    host_value_store: MutableMapping[str, Any],
) -> Optional[int]:
    restart_count_list = host_value_store.setdefault("restart_count_list", [])
    while restart_count_list and restart_count_list[0][0] <= curr_timestamp_seconds - ONE_HOUR:
        restart_count_list.pop(0)
    restart_count_list.append((curr_timestamp_seconds, restart_count))
    if len(restart_count_list) > 1:
        return restart_count - restart_count_list[0][1]
    return None


register.check_plugin(
    name="kube_pod_restarts",
    service_name="Restarts",
    sections=["kube_pod_containers"],
    discovery_function=discovery,
    check_function=check_kube_pod_restarts,
    check_default_parameters=_DEFAULT_PARAMS,
    check_ruleset_name="kube_pod_restarts",
)
