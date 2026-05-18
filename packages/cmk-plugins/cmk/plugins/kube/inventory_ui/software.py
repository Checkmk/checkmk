#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.inventory_ui.v1_unstable import (
    Alignment,
    BackgroundColor,
    BoolField,
    LabelColor,
    Node,
    Table,
    TextField,
    Title,
)


def _style_container_ready(
    value: bool,
) -> Iterable[Alignment | BackgroundColor | LabelColor]:
    yield Alignment.CENTER
    if value:
        yield LabelColor.BLACK
        yield BackgroundColor.GREEN
    else:
        yield LabelColor.WHITE
        yield BackgroundColor.DARK_GRAY


node_software_applications_kube = Node(
    name="software_applications_kube",
    path=["software", "applications", "kube"],
    title=Title("Kubernetes"),
)

node_software_applications_kube_cluster = Node(
    name="software_applications_kube_cluster",
    path=["software", "applications", "kube", "cluster"],
    title=Title("Cluster"),
    attributes={
        "version": TextField(Title("Version")),
    },
)

node_software_applications_kube_containers = Node(
    name="software_applications_kube_containers",
    path=["software", "applications", "kube", "containers"],
    title=Title("Containers"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "ready": BoolField(Title("Ready"), style=_style_container_ready),
            "restart_count": TextField(Title("Restart count")),
            "image": TextField(Title("Image")),
            "image_pull_policy": TextField(Title("Image pull policy")),
            "image_id": TextField(Title("Image ID")),
            "container_id": TextField(Title("Container ID")),
        },
    ),
)

node_software_applications_kube_daemonset = Node(
    name="software_applications_kube_daemonset",
    path=["software", "applications", "kube", "daemonset"],
    title=Title("DaemonSet"),
    attributes={
        "strategy": TextField(Title("StrategyType")),
        "match_labels": TextField(Title("matchLabels")),
        "match_expressions": TextField(Title("matchExpressions")),
    },
)

node_software_applications_kube_deployment = Node(
    name="software_applications_kube_deployment",
    path=["software", "applications", "kube", "deployment"],
    title=Title("Deployment"),
    attributes={
        "strategy": TextField(Title("StrategyType")),
        "match_labels": TextField(Title("matchLabels")),
        "match_expressions": TextField(Title("matchExpressions")),
    },
)

node_software_applications_kube_labels = Node(
    name="software_applications_kube_labels",
    path=["software", "applications", "kube", "labels"],
    title=Title("Labels"),
    table=Table(
        columns={
            "label_name": TextField(Title("Name")),
            "label_value": TextField(Title("Value")),
        },
    ),
)

node_software_applications_kube_metadata = Node(
    name="software_applications_kube_metadata",
    path=["software", "applications", "kube", "metadata"],
    title=Title("Metadata"),
    attributes={
        "object": TextField(Title("Object")),
        "name": TextField(Title("Name")),
        "namespace": TextField(Title("Namespace")),
    },
)

node_software_applications_kube_node = Node(
    name="software_applications_kube_node",
    path=["software", "applications", "kube", "node"],
    title=Title("Node"),
    attributes={
        "operating_system": TextField(Title("Operating system")),
        "os_image": TextField(Title("OS image")),
        "kernel_version": TextField(Title("Kernel version")),
        "architecture": TextField(Title("Architecture")),
        "container_runtime_version": TextField(Title("Container runtime version")),
        "kubelet_version": TextField(Title("Kubelet version")),
    },
)

node_software_applications_kube_pod = Node(
    name="software_applications_kube_pod",
    path=["software", "applications", "kube", "pod"],
    title=Title("Pod"),
    attributes={
        "dns_policy": TextField(Title("DNS policy")),
        "host_ip": TextField(Title("Host IP")),
        "host_network": TextField(Title("Host network")),
        "node": TextField(Title("Node")),
        "pod_ip": TextField(Title("Pod IP")),
        "qos_class": TextField(Title("QoS class")),
    },
)

node_software_applications_kube_statefulset = Node(
    name="software_applications_kube_statefulset",
    path=["software", "applications", "kube", "statefulset"],
    title=Title("StatefulSet"),
    attributes={
        "strategy": TextField(Title("StrategyType")),
        "match_labels": TextField(Title("matchLabels")),
        "match_expressions": TextField(Title("matchExpressions")),
    },
)
