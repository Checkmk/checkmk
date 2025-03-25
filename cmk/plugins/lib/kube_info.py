#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import Any, Literal, NewType

from cmk.agent_based.v2 import CheckResult, HostLabel, HostLabelGenerator, render, Result, State
from cmk.plugins.kube.schemata.section import (
    ControlChain,
    DaemonSetInfo,
    DeploymentInfo,
    StatefulSetInfo,
)
from cmk.plugins.lib.kube import kube_annotations_to_cmk_labels, kube_labels_to_cmk_labels


def result_simple(display_name: str, notice_only: bool = False) -> Callable[[object], Result]:
    key = "notice" if notice_only else "summary"

    def result_func(value: object) -> Result:
        return Result(state=State.OK, **{key: f"{display_name}: {value}"})

    return result_func


Age = NewType("Age", float)


def result_from_age(value: Age) -> Result:
    return Result(
        state=State.OK,
        summary=f"Age: {render.timespan(value)}",
    )


def result_from_control_chain(control_chain: ControlChain) -> Result:
    chain_display = " <- ".join(f"{c.type_}/{c.name}" for c in control_chain)
    return Result(
        state=State.OK, summary=f"Controlled by: {chain_display if chain_display else None}"
    )


InfoTypes = Literal[
    "name",
    "node",
    "namespace",
    "os_image",
    "container_runtime_version",
    "control_chain",
    "age",
    "qos_class",
    "uid",
    "restart_policy",
    "architecture",
    "kernel_version",
    "operating_system",
    "schedule",
    "concurrency_policy",
    "failed_jobs_history_limit",
    "successful_jobs_history_limit",
    "suspend",
]

_RESULT_FUNC: Mapping[InfoTypes, Callable[[Any], Result]] = {
    "name": result_simple("Name"),
    "node": result_simple("Node"),
    "namespace": result_simple("Namespace"),
    "schedule": result_simple("Schedule"),
    "age": result_from_age,
    "os_image": result_simple("OS"),
    "container_runtime_version": result_simple("Container runtime"),
    "control_chain": result_from_control_chain,
    "qos_class": result_simple("QoS class", notice_only=True),
    "uid": result_simple("UID", notice_only=True),
    "restart_policy": result_simple("Restart policy", notice_only=True),
    "architecture": result_simple("Architecture", notice_only=True),
    "kernel_version": result_simple("Kernel version", notice_only=True),
    "operating_system": result_simple("OS family", notice_only=True),
    "concurrency_policy": result_simple("Concurrency policy", notice_only=True),
    "failed_jobs_history_limit": result_simple("Failed jobs history limit", notice_only=True),
    "successful_jobs_history_limit": result_simple(
        "Successful jobs history limit", notice_only=True
    ),
    "suspend": result_simple("Suspend", notice_only=True),
}


def check_info(info: Mapping[InfoTypes, Any]) -> CheckResult:
    for info_type, function in _RESULT_FUNC.items():
        if info_type in info:
            yield function(info[info_type])


def host_labels(
    object_type: Literal["deployment", "daemonset", "statefulset"],
) -> Callable[[DaemonSetInfo | DeploymentInfo | StatefulSetInfo], HostLabelGenerator]:
    def _host_labels(
        section: DaemonSetInfo | DeploymentInfo | StatefulSetInfo,
    ) -> HostLabelGenerator:
        """Host label function.

        Labels:
            cmk/kubernetes:
                This label is set to "yes" for all Kubernetes objects.

            cmk/kubernetes/object:
                This label is set to the Kubernetes object type.

            cmk/kubernetes/cluster:
                This label is set to the given Kubernetes cluster name.

            cmk/kubernetes/namespace:
                This label contains the name of the Kubernetes Namespace this checkmk host is
                associated with.

            cmk/kubernetes/annotation/{key}:{value} :
                These labels are yielded for each Kubernetes annotation that is
                a valid Kubernetes label. This can be configured via the rule
                'Kubernetes'.

            cmk/kubernetes/deployment:
                This label is set to the name of the Deployment.

            cmk/kubernetes/daemonset:
                This label is set to the name of the DaemonSet.

            cmk/kubernetes/statefulset:
                This label is set to the name of the StatefulSet.

            cmk/kubernetes/cluster-host:
                This label contains the name of the Checkmk host which represents the
                Kubernetes cluster.

        """

        yield HostLabel("cmk/kubernetes", "yes")
        yield HostLabel("cmk/kubernetes/object", object_type)
        yield HostLabel("cmk/kubernetes/cluster", section.cluster)
        yield HostLabel("cmk/kubernetes/namespace", section.namespace)
        yield HostLabel(f"cmk/kubernetes/{object_type}", section.name)
        yield HostLabel("cmk/kubernetes/cluster-host", section.kubernetes_cluster_hostname)
        yield from kube_annotations_to_cmk_labels(section.annotations)
        yield from kube_labels_to_cmk_labels(section.labels)

    return _host_labels
