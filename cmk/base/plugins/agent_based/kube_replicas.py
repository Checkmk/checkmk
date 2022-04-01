#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Any, Literal, Mapping, MutableMapping, Optional, Tuple, Union

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.kube import (
    DaemonSetReplicas,
    DeploymentReplicas,
    StatefulSetReplicas,
    UpdateStrategy,
    VSResultAge,
)
from .utils.kube_strategy import strategy_text


def parse_kube_deployment_replicas(string_table: StringTable) -> DeploymentReplicas:
    return DeploymentReplicas(**json.loads(string_table[0][0]))


def parse_kube_statefulset_replicas(string_table: StringTable) -> StatefulSetReplicas:
    return StatefulSetReplicas(**json.loads(string_table[0][0]))


def parse_kube_daemonset_replicas(string_table: StringTable) -> DaemonSetReplicas:
    return DaemonSetReplicas(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_deployment_replicas_v1",
    parsed_section_name="kube_replicas",
    parse_function=parse_kube_deployment_replicas,
)

register.agent_section(
    name="kube_statefulset_replicas_v1",
    parsed_section_name="kube_replicas",
    parse_function=parse_kube_statefulset_replicas,
)

register.agent_section(
    name="kube_daemonset_replicas_v1",
    parsed_section_name="kube_replicas",
    parse_function=parse_kube_daemonset_replicas,
)


def parse_kube_strategy(string_table: StringTable) -> UpdateStrategy:
    return UpdateStrategy(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_update_strategy_v1",
    parsed_section_name="kube_update_strategy",
    parse_function=parse_kube_strategy,
)

Replicas = Union[DeploymentReplicas, StatefulSetReplicas, DaemonSetReplicas]


def discover_kube_replicas(
    section_kube_replicas: Optional[Replicas],
    section_kube_update_strategy: Optional[UpdateStrategy],
) -> DiscoveryResult:
    if section_kube_replicas is not None:
        yield Service()


def _check_duration(
    transition_complete: bool,
    value_store_key: Literal["not_ready_started_timestamp", "update_started_timestamp"],
    now: float,
    value_store: MutableMapping[str, Any],
    levels_upper: Optional[Tuple[int, int]],
    label: str,
) -> CheckResult:
    """Update/read value_store and check the duration of undesired replica states.

    This function has side effects: It mutates the value_store.
    """

    if transition_complete:
        value_store[value_store_key] = None
        return
    ts = value_store.get(value_store_key) or now
    value_store[value_store_key] = ts

    yield from check_levels(
        now - ts,
        levels_upper=levels_upper,
        render_func=render.timespan,
        label=label,
    )


def _levels(
    params: Mapping[str, VSResultAge],
    param_name: str,
) -> Optional[Tuple[int, int]]:
    if (levels_upper := params.get(param_name, "no_levels")) == "no_levels":
        return None
    return levels_upper[1]


def check_kube_replicas(
    params: Mapping[str, VSResultAge],
    section_kube_replicas: Optional[Replicas],
    section_kube_update_strategy: Optional[UpdateStrategy],
) -> CheckResult:
    yield from _check_kube_replicas(
        params,
        section_kube_replicas,
        section_kube_update_strategy,
        now=time.time(),
        value_store=get_value_store(),
    )


def _check_kube_replicas(
    params: Mapping[str, VSResultAge],
    section_kube_replicas: Optional[Replicas],
    section_kube_update_strategy: Optional[UpdateStrategy],
    *,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:

    if section_kube_replicas is None:
        return

    yield Result(
        state=State.OK,
        summary=f"Ready: {section_kube_replicas.ready}/{section_kube_replicas.desired}",
    )

    yield Result(
        state=State.OK,
        summary=f"Up-to-date: {section_kube_replicas.updated}/{section_kube_replicas.desired}",
    )

    metric_boundary = (0, section_kube_replicas.desired)
    yield Metric("kube_desired_replicas", section_kube_replicas.desired, boundaries=metric_boundary)
    yield Metric("kube_ready_replicas", section_kube_replicas.ready, boundaries=metric_boundary)
    yield Metric("kube_updated_replicas", section_kube_replicas.updated, boundaries=metric_boundary)

    yield from _check_duration(
        section_kube_replicas.ready == section_kube_replicas.desired,
        "not_ready_started_timestamp",
        now,
        value_store,
        _levels(params, "not_ready_duration"),
        "Not ready for",
    )

    all_updated = section_kube_replicas.updated == section_kube_replicas.desired
    yield from _check_duration(
        all_updated,
        "update_started_timestamp",
        now,
        value_store,
        _levels(params, "update_duration"),
        "Not updated for",
    )

    if section_kube_update_strategy is None or all_updated:
        return

    yield Result(
        state=State.OK,
        summary=f"Strategy: {strategy_text(section_kube_update_strategy.strategy)}",
    )


register.check_plugin(
    name="kube_replicas",
    sections=["kube_replicas", "kube_update_strategy"],
    service_name="Replicas",
    discovery_function=discover_kube_replicas,
    check_function=check_kube_replicas,
    check_ruleset_name="kube_replicas",
    check_default_parameters={
        "update_duration": ("levels", (300, 600)),
        "not_ready_duration": ("levels", (300, 600)),
    },
)
