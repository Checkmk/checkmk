#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Any, Mapping, Optional, Tuple

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
from .utils.k8s import DeploymentSpec, Replicas


def parse_kube_replicas(string_table: StringTable) -> Replicas:
    return Replicas(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_replicas_v1",
    parsed_section_name="kube_replicas",
    parse_function=parse_kube_replicas,
)


def parse_kube_deployment_spec(string_table: StringTable) -> DeploymentSpec:
    return DeploymentSpec(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_deployment_spec_v1",
    parsed_section_name="kube_deployment_spec",
    parse_function=parse_kube_deployment_spec,
)


def discover_kube_replicas(
    section_kube_replicas: Optional[Replicas],
    section_kube_deployment_spec: Optional[DeploymentSpec],
) -> DiscoveryResult:
    if section_kube_replicas is not None:
        yield Service()


def _check_duration(
    reference_ts: Optional[float],
    now: float,
    levels_upper: Optional[Tuple[int, int]],
    label: str,
) -> CheckResult:
    if reference_ts is None:
        return

    yield from check_levels(
        now - reference_ts,
        levels_upper=levels_upper,
        render_func=render.timespan,
        label=label,
    )


def _levels(params: Mapping[str, Any], param_name: str) -> Optional[Tuple[int, int]]:
    if (levels_upper := params.get(param_name, "no_levels")) == "no_levels":
        return None
    return levels_upper[1]


def check_kube_replicas(
    params: Mapping[str, Any],
    section_kube_replicas: Optional[Replicas],
    section_kube_deployment_spec: Optional[DeploymentSpec],
) -> CheckResult:

    if section_kube_replicas is None:
        return

    yield Result(
        state=State.OK,
        summary=f"Ready: {section_kube_replicas.ready}/{section_kube_replicas.replicas}",
    )

    yield Result(
        state=State.OK,
        summary=f"Up-to-date: {section_kube_replicas.updated}/{section_kube_replicas.replicas}",
    )

    metric_boundary = (0, section_kube_replicas.replicas)
    yield Metric(
        "kube_desired_replicas", section_kube_replicas.replicas, boundaries=metric_boundary
    )
    yield Metric("kube_ready_replicas", section_kube_replicas.ready, boundaries=metric_boundary)
    yield Metric("kube_updated_replicas", section_kube_replicas.updated, boundaries=metric_boundary)

    value_store = get_value_store()
    now = time.time()

    all_ready = section_kube_replicas.ready == section_kube_replicas.replicas
    not_ready_started_ts = (
        None if all_ready else value_store.get("not_ready_started_timestamp", now)
    )
    value_store["not_ready_started_timestamp"] = not_ready_started_ts

    all_updated = section_kube_replicas.updated == section_kube_replicas.replicas
    update_started_ts = None if all_updated else value_store.get("update_started_timestamp", now)
    value_store["update_started_timestamp"] = update_started_ts

    if all_ready and all_updated:
        return

    yield from _check_duration(
        not_ready_started_ts,
        now,
        _levels(params, "not_ready_duration"),
        "Not ready for",
    )

    yield from _check_duration(
        update_started_ts,
        now,
        _levels(params, "update_duration"),
        "Not updated for",
    )

    if section_kube_deployment_spec is None or all_updated:
        return

    if section_kube_deployment_spec.strategy.rolling_update:
        rolling_update_text = (
            f" (max surge: {section_kube_deployment_spec.strategy.rolling_update.max_surge}, "
            f"max unavailable: {section_kube_deployment_spec.strategy.rolling_update.max_unavailable})"
        )

    yield Result(
        state=State.OK,
        summary=f"Strategy: {section_kube_deployment_spec.strategy.type_}{rolling_update_text}",
    )


register.check_plugin(
    name="kube_replicas",
    sections=["kube_replicas", "kube_deployment_spec"],
    service_name="Replicas",
    discovery_function=discover_kube_replicas,
    check_function=check_kube_replicas,
    check_ruleset_name="kube_replicas",
    check_default_parameters={
        "update_duration": ("levels", (300, 600)),
        "not_ready_duration": ("levels", (300, 600)),
    },
)
