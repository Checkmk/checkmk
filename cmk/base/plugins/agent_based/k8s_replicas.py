#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
import time
from typing import Dict, Union

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    HostLabel,
    IgnoreResultsError,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, HostLabelGenerator
from .utils import k8s

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


def host_labels(section: Dict) -> HostLabelGenerator:
    if section["ready_replicas"] is not None and section["replicas"] is not None:
        yield HostLabel("cmk/kubernetes_object", "deployment")
        yield HostLabel("cmk/kubernetes", "yes")


register.agent_section(
    name="k8s_replicas",
    parse_function=k8s.parse_json,
    host_label_function=host_labels,
)


def parse_k8s_surge(value: Union[str, int], total: int) -> int:
    """
    Returns the upper level for replicas which is considered critical
    (hence the +1 in the return value). Values may be given as an
    absolute number or in percent.
    """
    if isinstance(value, int):
        return value + total + 1
    percentage = 1.0 + float(value.rstrip("%")) / 100.0
    return math.ceil(percentage * total) + 1


def parse_k8s_unavailability(value: Union[str, int], total: int) -> int:
    """
    Returns the lower level for replicas which is still considered ok.
    Values may be given as an absolute number or in percent.
    """
    if isinstance(value, int):
        return total - value
    percentage = 1.0 - float(value.rstrip("%")) / 100.0
    return math.floor(percentage * total)


def discover_k8s_replicas(section) -> DiscoveryResult:
    # the deployment must either be paused or return numbers for running pods
    if (section["ready_replicas"] is not None and section["replicas"] is not None) or section[
        "paused"
    ]:
        yield Service()


def check_k8s_replicas(section) -> CheckResult:
    ready, total = section["ready_replicas"], section["replicas"]
    paused, strategy = section["paused"], section["strategy_type"]
    value_store = get_value_store()

    if total is None or ready is None:
        first_unavailable_time = value_store.get("unavailable")
        if first_unavailable_time:
            age = time.time() - first_unavailable_time
            yield from check_levels(
                age,
                levels_upper=(
                    600,
                    600,
                ),  # setting 10 minutes as default threshold for missing replica data
                render_func=render.timespan,
                label="The replicas data has been missing",
            )
            return
        value_store["unavailable"] = time.time()
        raise IgnoreResultsError("The replicas data is currently unavailable")

    # previously missing but now complete data
    if value_store.get("unavailable"):
        value_store["unavailable"] = None

    if paused or strategy == "Recreate":
        levels_upper = None
        levels_lower = None
    elif strategy == "RollingUpdate":
        crit = parse_k8s_surge(section["max_surge"], total)
        levels_upper = crit, crit
        crit_lower = parse_k8s_unavailability(section["max_unavailable"], total)
        levels_lower = crit_lower, crit_lower
    else:
        yield Result(state=State.UNKNOWN, summary=f"Unknown deployment strategy: {strategy}")
        return

    yield from check_levels(
        ready,
        metric_name="ready_replicas",
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        boundaries=(0, total),
        render_func=lambda r: f"{r}/{total}",
        label="Ready",
    )

    if paused:
        yield Result(state=State.OK, summary="Paused")

    yield Metric("total_replicas", total)

    if strategy:
        summary = f"Strategy: {section['strategy_type']}"
        if strategy == "RollingUpdate":
            summary = f"{summary} (max unavailable: {section['max_unavailable']}, max surge: {section['max_surge']})"
        yield Result(state=State.OK, summary=summary)


register.check_plugin(
    name="k8s_replicas",
    service_name="Replicas",
    discovery_function=discover_k8s_replicas,
    check_function=check_k8s_replicas,
)
