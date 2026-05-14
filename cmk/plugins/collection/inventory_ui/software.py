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
    NumberField,
    Table,
    TextField,
    Title,
    View,
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


node_software_applications_azure_application_gateways = Node(
    name="software_applications_azure_application_gateways",
    path=["software", "applications", "azure", "application_gateways"],
    title=Title("Application gateways"),
)

node_software_applications_azure_application_gateways_rules = Node(
    name="software_applications_azure_application_gateways_rules",
    path=["software", "applications", "azure", "application_gateways", "rules"],
    title=Title("Rules"),
)

node_software_applications_azure_application_gateways_rules_backends = Node(
    name="software_applications_azure_application_gateways_rules_backends",
    path=["software", "applications", "azure", "application_gateways", "rules", "backends"],
    title=Title("Back-ends"),
    table=Table(
        columns={
            "application_gateway": TextField(Title("Application gateway")),
            "rule": TextField(Title("Rule")),
            "address_pool_name": TextField(Title("Address pool name")),
            "protocol": TextField(Title("Protocol")),
            "port": TextField(Title("Port")),
        },
    ),
)

node_software_applications_azure_application_gateways_rules_listeners = Node(
    name="software_applications_azure_application_gateways_rules_listeners",
    path=["software", "applications", "azure", "application_gateways", "rules", "listeners"],
    title=Title("Listeners"),
    table=Table(
        columns={
            "application_gateway": TextField(Title("Application gateway")),
            "rule": TextField(Title("Rule")),
            "listener": TextField(Title("Listener")),
            "protocol": TextField(Title("Protocol")),
            "port": TextField(Title("Port")),
            "host_names": TextField(Title("Hosts")),
        },
    ),
)

node_software_applications_azure_application_gateways_rules_listeners_private_ips = Node(
    name="software_applications_azure_application_gateways_rules_listeners_private_ips",
    path=[
        "software",
        "applications",
        "azure",
        "application_gateways",
        "rules",
        "listeners",
        "private_ips",
    ],
    title=Title("Private IPs"),
    table=Table(
        columns={
            "application_gateway": TextField(Title("Application gateway")),
            "rule": TextField(Title("Rule")),
            "listener": TextField(Title("Listener")),
            "ip_address": TextField(Title("IP address")),
            "allocation_method": TextField(Title("Allocation method")),
        },
    ),
)

node_software_applications_azure_application_gateways_rules_listeners_public_ips = Node(
    name="software_applications_azure_application_gateways_rules_listeners_public_ips",
    path=[
        "software",
        "applications",
        "azure",
        "application_gateways",
        "rules",
        "listeners",
        "public_ips",
    ],
    title=Title("Public IPs"),
    table=Table(
        columns={
            "application_gateway": TextField(Title("Application gateway")),
            "rule": TextField(Title("Rule")),
            "listener": TextField(Title("Listener")),
            "name": TextField(Title("Name")),
            "location": TextField(Title("Location")),
            "ip_address": TextField(Title("IP address")),
            "allocation_method": TextField(Title("Allocation method")),
            "dns_fqdn": TextField(Title("DNS FQDN")),
        },
    ),
)

node_software_applications_azure_metadata = Node(
    name="software_applications_azure_metadata",
    path=["software", "applications", "azure", "metadata"],
    title=Title("Metadata"),
    attributes={
        "object": TextField(Title("Object")),
        "name": TextField(Title("Name")),
        "entity": TextField(Title("Entity")),
        "resource_group": TextField(Title("Resource group")),
        "subscription_id": TextField(Title("Subscription ID")),
        "subscription_name": TextField(Title("Subscription name")),
        "region": TextField(Title("Region")),
        "tenant_id": TextField(Title("Tenant ID")),
        "tenant_name": TextField(Title("Tenant Name")),
    },
)

node_software_applications_check_mk_cluster = Node(
    name="software_applications_check_mk_cluster",
    path=["software", "applications", "check_mk", "cluster"],
    title=Title("Cluster"),
    attributes={
        "is_cluster": BoolField(Title("Cluster host")),
    },
)

node_software_applications_check_mk_cluster_nodes = Node(
    name="software_applications_check_mk_cluster_nodes",
    path=["software", "applications", "check_mk", "cluster", "nodes"],
    title=Title("Nodes"),
    table=Table(
        columns={
            "name": TextField(Title("Node name")),
        },
    ),
)

node_software_applications_checkmk_agent_local_checks = Node(
    name="software_applications_checkmk_agent_local_checks",
    path=["software", "applications", "checkmk-agent", "local_checks"],
    title=Title("Local checks"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
            "cache_interval": TextField(Title("Cache interval")),
        },
    ),
)


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

node_software_applications_synthetic_monitoring = Node(
    name="software_applications_synthetic_monitoring",
    path=["software", "applications", "synthetic_monitoring"],
    title=Title("Synthetic monitoring"),
)

node_software_applications_synthetic_monitoring_plans = Node(
    name="software_applications_synthetic_monitoring_plans",
    path=["software", "applications", "synthetic_monitoring", "plans"],
    title=Title("Plans"),
    table=Table(
        view=View(name="invsyntheticmonitoringplans", title=Title("Plans")),
        columns={
            "application": TextField(Title("Application")),
            "suite_name": TextField(Title("Suite name")),
            "variant": TextField(Title("Variant")),
            "plan_id": TextField(Title("Plan ID")),
        },
    ),
)

node_software_applications_synthetic_monitoring_tests = Node(
    name="software_applications_synthetic_monitoring_tests",
    path=["software", "applications", "synthetic_monitoring", "tests"],
    title=Title("Tests"),
    table=Table(
        view=View(name="invsyntheticmonitoringtests", title=Title("Tests")),
        columns={
            "application": TextField(Title("Application")),
            "suite_name": TextField(Title("Suite name")),
            "variant": TextField(Title("Variant")),
            "top_level_suite_name": TextField(Title("Top level suite")),
            "bottom_level_suite_name": TextField(Title("Bottom level suite")),
            "test_name": TextField(Title("Test")),
            "plan_id": TextField(Title("Plan ID")),
            "test_item": TextField(Title("Item")),
        },
    ),
)

node_software_applications_synthetic_monitoring_scheduler = Node(
    name="software_applications_synthetic_monitoring_scheduler",
    path=["software", "applications", "synthetic_monitoring", "scheduler"],
    title=Title("Scheduler"),
)

node_software_applications_synthetic_monitoring_scheduler_config = Node(
    name="software_applications_synthetic_monitoring_scheduler_config",
    path=["software", "applications", "synthetic_monitoring", "scheduler", "config"],
    title=Title("Scheduler plan configs"),
    table=Table(
        columns={
            "scheduler_interval": NumberField(Title("Scheduler interval")),
            "env_creation": TextField(Title("Env creation")),
            "n_attempts_max": NumberField(Title("Maximum number of attempts")),
            "robot_type": TextField(Title("Robot")),
            "assigned_to_host": TextField(Title("Assigned to host")),
            "plan_id": TextField(Title("Plan ID")),
        },
    ),
)
node_software_applications_vmwareesx = Node(
    name="software_applications_vmwareesx",
    path=["software", "applications", "vmwareesx"],
    title=Title("VMware ESX"),
    table=Table(
        columns={
            "clusters": TextField(Title("Clusters")),
        },
    ),
)

node_software_applications_proxmox_ve = Node(
    name="software_applications_proxmox_ve",
    path=["software", "applications", "proxmox_ve"],
    title=Title("Proxmox"),
)

node_software_applications_proxmox_ve_metadata = Node(
    name="software_applications_proxmox_ve_metadata",
    path=["software", "applications", "proxmox_ve", "metadata"],
    title=Title("Metadata"),
    attributes={
        "object": TextField(Title("Object")),
        "provider": TextField(Title("Provider")),
        "name": TextField(Title("Name")),
        "node": TextField(Title("Node")),
    },
)

node_software_applications_proxmox_ve_cluster = Node(
    name="software_applications_proxmox_ve_cluster",
    path=["software", "applications", "proxmox_ve", "cluster"],
    title=Title("Cluster"),
    attributes={
        "cluster": TextField(Title("Cluster name")),
    },
)
