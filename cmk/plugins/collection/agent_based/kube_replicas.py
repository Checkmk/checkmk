#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping
from typing import Any, Literal

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.kube.schemata.section import (
    ControllerSpec,
    DaemonSetReplicas,
    DeploymentReplicas,
    StatefulSetReplicas,
    UpdateStrategy,
)
from cmk.plugins.lib.kube import VSResultAge
from cmk.plugins.lib.kube_strategy import strategy_text


def parse_kube_deployment_replicas(string_table: StringTable) -> DeploymentReplicas:
    return DeploymentReplicas.model_validate_json(string_table[0][0])


def parse_kube_statefulset_replicas(string_table: StringTable) -> StatefulSetReplicas:
    return StatefulSetReplicas.model_validate_json(string_table[0][0])


def parse_kube_daemonset_replicas(string_table: StringTable) -> DaemonSetReplicas:
    return DaemonSetReplicas.model_validate_json(string_table[0][0])


agent_section_kube_deployment_replicas_v1 = AgentSection(
    name="kube_deployment_replicas_v1",
    parsed_section_name="kube_replicas",
    parse_function=parse_kube_deployment_replicas,
)

agent_section_kube_statefulset_replicas_v1 = AgentSection(
    name="kube_statefulset_replicas_v1",
    parsed_section_name="kube_replicas",
    parse_function=parse_kube_statefulset_replicas,
)

agent_section_kube_daemonset_replicas_v1 = AgentSection(
    name="kube_daemonset_replicas_v1",
    parsed_section_name="kube_replicas",
    parse_function=parse_kube_daemonset_replicas,
)


def parse_kube_strategy(string_table: StringTable) -> UpdateStrategy:
    return UpdateStrategy.model_validate_json(string_table[0][0])


agent_section_kube_update_strategy_v1 = AgentSection(
    name="kube_update_strategy_v1",
    parsed_section_name="kube_update_strategy",
    parse_function=parse_kube_strategy,
)


def parse_kube_controller_spec(string_table: StringTable) -> ControllerSpec:
    return ControllerSpec.model_validate_json(string_table[0][0])


agent_section_kube_controller_spec_v1 = AgentSection(
    name="kube_controller_spec_v1",
    parsed_section_name="kube_controller_spec",
    parse_function=parse_kube_controller_spec,
)

Replicas = DeploymentReplicas | StatefulSetReplicas | DaemonSetReplicas


def discover_kube_replicas(
    section_kube_replicas: Replicas | None,
    section_kube_update_strategy: UpdateStrategy | None,
    section_kube_controller_spec: ControllerSpec | None,
) -> DiscoveryResult:
    if section_kube_replicas is not None:
        yield Service()


def _check_duration(
    transition_complete: bool,
    value_store_key: Literal[
        "not_available_started_timestamp",
        "not_ready_started_timestamp",
        "update_started_timestamp",
        "misscheduled_timestamp",
    ],
    now: float,
    value_store: MutableMapping[str, Any],
    levels_upper: tuple[int, int] | None,
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

    yield from check_levels_v1(
        now - ts,
        levels_upper=levels_upper,
        render_func=render.timespan,
        label=label,
    )


def _levels(
    params: Mapping[str, VSResultAge],
    param_name: str,
) -> tuple[int, int] | None:
    if (levels_upper := params.get(param_name, "no_levels")) == "no_levels":
        return None
    return levels_upper[1]


def check_kube_replicas(
    params: Mapping[str, VSResultAge],
    section_kube_replicas: Replicas | None,
    section_kube_update_strategy: UpdateStrategy | None,
    section_kube_controller_spec: ControllerSpec | None,
) -> CheckResult:
    yield from _check_kube_replicas(
        params,
        section_kube_replicas,
        section_kube_update_strategy,
        section_kube_controller_spec,
        now=time.time(),
        value_store=get_value_store(),
    )


def _check_kube_replicas(
    params: Mapping[str, VSResultAge],
    section_kube_replicas: Replicas | None,
    section_kube_update_strategy: UpdateStrategy | None,
    section_kube_controller_spec: ControllerSpec | None,
    *,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if section_kube_replicas is None:
        return

    metric_boundary = (0, section_kube_replicas.desired)

    if (
        section_kube_controller_spec is not None
        and section_kube_controller_spec.min_ready_seconds > 0
    ):
        yield Result(
            state=State.OK,
            summary=f"Available: {section_kube_replicas.available}/{section_kube_replicas.desired}",
        )
        yield Metric(
            "kube_available_replicas", section_kube_replicas.available, boundaries=metric_boundary
        )

    yield Result(
        state=State.OK,
        summary=f"Ready: {section_kube_replicas.ready}/{section_kube_replicas.desired}",
    )
    yield Result(
        state=State.OK,
        summary=f"Up-to-date: {section_kube_replicas.updated}/{section_kube_replicas.desired}",
    )

    yield Metric("kube_desired_replicas", section_kube_replicas.desired, boundaries=metric_boundary)
    yield Metric("kube_ready_replicas", section_kube_replicas.ready, boundaries=metric_boundary)
    yield Metric("kube_updated_replicas", section_kube_replicas.updated, boundaries=metric_boundary)

    if isinstance(section_kube_replicas, DaemonSetReplicas):
        yield Result(
            state=State.OK,
            summary=f"Misscheduled: {section_kube_replicas.misscheduled}",
        )
        yield Metric("kube_misscheduled_replicas", section_kube_replicas.misscheduled)

    if (
        section_kube_controller_spec is not None
        and section_kube_controller_spec.min_ready_seconds > 0
    ):
        yield from _check_duration(
            section_kube_replicas.available == section_kube_replicas.desired,
            "not_available_started_timestamp",
            now,
            value_store,
            _levels(params, "not_available_duration"),
            "Not available for",
        )

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

    if isinstance(section_kube_replicas, DaemonSetReplicas):
        yield from _check_duration(
            section_kube_replicas.misscheduled == 0,
            "misscheduled_timestamp",
            now,
            value_store,
            _levels(params, "misscheduled_duration"),
            "Misscheduled for",
        )

    if section_kube_update_strategy is None or all_updated:
        return

    yield Result(
        state=State.OK,
        summary=f"Strategy: {strategy_text(section_kube_update_strategy.strategy)}",
    )


check_plugin_kube_replicas = CheckPlugin(
    name="kube_replicas",
    sections=["kube_replicas", "kube_update_strategy", "kube_controller_spec"],
    service_name="Replicas",
    discovery_function=discover_kube_replicas,
    check_function=check_kube_replicas,
    check_ruleset_name="kube_replicas",
    check_default_parameters={
        "update_duration": ("levels", (300, 600)),
        "not_ready_duration": ("levels", (300, 600)),
        "misscheduled_duration": ("levels", (300, 600)),
    },
)
