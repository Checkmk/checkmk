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
            if age > 600:  # setting 10 minutes as default threshold for missing replica data
                yield from check_levels(
                    age,
                    levels_upper=(600, 600),
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
        crit, crit_lower = None, None
    elif strategy == "RollingUpdate":
        crit = parse_k8s_surge(section["max_surge"], total)
        crit_lower = parse_k8s_unavailability(section["max_unavailable"], total)
    else:
        yield Result(state=State.UNKNOWN, summary=f"Unknown deployment strategy: {strategy}")
        return

    state = 0
    infotext = "Ready: %s/%s" % (ready, total)
    if paused:
        infotext += " (paused)"
    if crit is not None and ready >= crit:
        state = 2
        infotext += " (crit at %d)" % crit
    if crit_lower is not None and ready < crit_lower:
        state = 2
        infotext += " (crit below %d)" % crit_lower

    yield Result(state=State(state), summary=infotext)
    for metric_name, metric_value, levels_warn, levels_crit, lower_boundary, upper_boundary in [
        ("ready_replicas", ready, None, crit, 0, total),
        ("total_replicas", total, None, None, None, None),
    ]:
        yield Metric(
            metric_name,
            metric_value,
            levels=(levels_warn, levels_crit),
            boundaries=(lower_boundary, upper_boundary),
        )

    if strategy:
        strategy_infotext = "Strategy: %s" % section["strategy_type"]
        if strategy == "RollingUpdate":
            strategy_infotext += " (max unavailable: %s, max surge: %s)" % (
                section["max_unavailable"],
                section["max_surge"],
            )
        yield Result(state=State.OK, summary=strategy_infotext)


register.check_plugin(
    name="k8s_replicas",
    service_name="Replicas",
    discovery_function=discover_k8s_replicas,
    check_function=check_k8s_replicas,
)
