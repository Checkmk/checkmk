#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.inventory_ui.v1_alpha import (
    AgeNotation,
    BoolField,
    DecimalNotation,
    Label,
    Node,
    NumberField,
    SINotation,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_AGE = Unit(AgeNotation())
UNIT_BYTES = Unit(SINotation("B"))
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))


def _render_date(value: int | float) -> Label | str:
    return str(time.strftime("%Y-%m-%d", time.localtime(value)))


node_software = Node(
    name="software",
    path=["software"],
    title=Title("Software"),
)

node_software_applications = Node(
    name="software_applications",
    path=["software", "applications"],
    title=Title("Applications"),
)

node_software_applications_azure = Node(
    name="software_applications_azure",
    path=["software", "applications", "azure"],
    title=Title("Azure"),
)

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
    title=Title("Backends"),
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

node_software_applications_azure_load_balancers = Node(
    name="software_applications_azure_load_balancers",
    path=["software", "applications", "azure", "load_balancers"],
    title=Title("Load balancers"),
)

node_software_applications_azure_load_balancers_inbound_nat_rules = Node(
    name="software_applications_azure_load_balancers_inbound_nat_rules",
    path=["software", "applications", "azure", "load_balancers", "inbound_nat_rules"],
    title=Title("Inbound NAT rules"),
    table=Table(
        columns={
            "load_balancer": TextField(Title("Load balancer")),
            "inbound_nat_rule": TextField(Title("Inbound NAT rule")),
            "frontend_port": TextField(Title("Frontend port")),
            "backend_port": TextField(Title("Backend port")),
        },
    ),
)

node_software_applications_azure_load_balancers_inbound_nat_rules_backend_ip_configs = Node(
    name="software_applications_azure_load_balancers_inbound_nat_rules_backend_ip_configs",
    path=[
        "software",
        "applications",
        "azure",
        "load_balancers",
        "inbound_nat_rules",
        "backend_ip_configs",
    ],
    title=Title("Public IPs"),
    table=Table(
        columns={
            "load_balancer": TextField(Title("Load balancer")),
            "inbound_nat_rule": TextField(Title("Inbound NAT rule")),
            "backend_ip_config": TextField(Title("Backend IP config")),
            "ip_address": TextField(Title("IP address")),
            "ip_allocation_method": TextField(Title("Allocation method")),
        },
    ),
)

node_software_applications_azure_load_balancers_inbound_nat_rules_private_ips = Node(
    name="software_applications_azure_load_balancers_inbound_nat_rules_private_ips",
    path=[
        "software",
        "applications",
        "azure",
        "load_balancers",
        "inbound_nat_rules",
        "private_ips",
    ],
    title=Title("Private IPs"),
    table=Table(
        columns={
            "load_balancer": TextField(Title("Load balancer")),
            "inbound_nat_rule": TextField(Title("Inbound NAT rule")),
            "ip_address": TextField(Title("IP address")),
            "ip_allocation_method": TextField(Title("Allocation method")),
        },
    ),
)

node_software_applications_azure_load_balancers_inbound_nat_rules_public_ips = Node(
    name="software_applications_azure_load_balancers_inbound_nat_rules_public_ips",
    path=["software", "applications", "azure", "load_balancers", "inbound_nat_rules", "public_ips"],
    title=Title("Public IPs"),
    table=Table(
        columns={
            "load_balancer": TextField(Title("Load balancer")),
            "inbound_nat_rule": TextField(Title("Inbound NAT rule")),
            "location": TextField(Title("Location")),
            "public_ip_name": TextField(Title("Name")),
            "ip_address": TextField(Title("IP Address")),
            "ip_allocation_method": TextField(Title("Allocation method")),
            "dns_fqdn": TextField(Title("DNS FQDN")),
        },
    ),
)

node_software_applications_azure_load_balancers_outbound_rules = Node(
    name="software_applications_azure_load_balancers_outbound_rules",
    path=["software", "applications", "azure", "load_balancers", "outbound_rules"],
    title=Title("Outbound rules"),
    table=Table(
        columns={
            "load_balancer": TextField(Title("Load balancer")),
            "outbound_rule": TextField(Title("Outbound rule")),
            "protocol": TextField(Title("Protocol")),
            "idle_timeout": TextField(Title("Idle timeout")),
        },
    ),
)

node_software_applications_azure_load_balancers_outbound_rules_backend_pools = Node(
    name="software_applications_azure_load_balancers_outbound_rules_backend_pools",
    path=["software", "applications", "azure", "load_balancers", "outbound_rules", "backend_pools"],
    title=Title("Backend pools"),
    table=Table(
        columns={
            "load_balancer": TextField(Title("Load balancer")),
            "outbound_rule": TextField(Title("Outbound rule")),
            "backend_pool": TextField(Title("Backend pool")),
        },
    ),
)

node_software_applications_azure_load_balancers_outbound_rules_backend_pools_addresses = Node(
    name="software_applications_azure_load_balancers_outbound_rules_backend_pools_addresses",
    path=[
        "software",
        "applications",
        "azure",
        "load_balancers",
        "outbound_rules",
        "backend_pools",
        "addresses",
    ],
    title=Title("Addresses"),
    table=Table(
        columns={
            "load_balancer": TextField(Title("Load balancer")),
            "outbound_rule": TextField(Title("Outbound rule")),
            "backend_pool": TextField(Title("Backend pool")),
            "address_name": TextField(Title("Address name")),
            "ip_address": TextField(Title("IP address")),
            "ip_allocation_method": TextField(Title("Allocation method")),
            "primary": TextField(Title("Primary")),
        },
    ),
)

node_software_applications_check_mk = Node(
    name="software_applications_check_mk",
    path=["software", "applications", "check_mk"],
    title=Title("Checkmk"),
    attributes={
        "num_hosts": TextField(Title("#Hosts")),
        "num_services": TextField(Title("#Services")),
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

node_software_applications_check_mk_versions = Node(
    name="software_applications_check_mk_versions",
    path=["software", "applications", "check_mk", "versions"],
    title=Title("Checkmk versions"),
    table=Table(
        view=View(name="invcmkversions", title=Title("Checkmk versions")),
        columns={
            "version": TextField(Title("Version")),
            "number": TextField(Title("Number")),
            "edition": TextField(Title("Edition")),
            "demo": BoolField(Title("Demo")),
            "num_sites": NumberField(Title("#Sites"), render=UNIT_COUNT),
        },
    ),
)

node_software_applications_checkmk_agent = Node(
    name="software_applications_checkmk_agent",
    path=["software", "applications", "checkmk-agent"],
    title=Title("Checkmk Agent"),
    attributes={
        "version": TextField(Title("Version")),
        "agentdirectory": TextField(Title("Agent directory")),
        "datadirectory": TextField(Title("Data directory")),
        "spooldirectory": TextField(Title("Spool directory")),
        "pluginsdirectory": TextField(Title("Plug-ins directory")),
        "localdirectory": TextField(Title("Local directory")),
        "agentcontroller": TextField(Title("Agent controller")),
    },
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

node_software_applications_checkmk_agent_plugins = Node(
    name="software_applications_checkmk_agent_plugins",
    path=["software", "applications", "checkmk-agent", "plugins"],
    title=Title("Agent plug-ins"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
            "cache_interval": TextField(Title("Cache interval")),
        },
    ),
)

node_software_applications_citrix = Node(
    name="software_applications_citrix",
    path=["software", "applications", "citrix"],
    title=Title("Citrix"),
)

node_software_applications_citrix_controller = Node(
    name="software_applications_citrix_controller",
    path=["software", "applications", "citrix", "controller"],
    title=Title("Controller"),
    attributes={
        "controller_version": TextField(Title("Controller version")),
    },
)

node_software_applications_citrix_vm = Node(
    name="software_applications_citrix_vm",
    path=["software", "applications", "citrix", "vm"],
    title=Title("Virtual machine"),
    attributes={
        "desktop_group_name": TextField(Title("Desktop group name")),
        "catalog": TextField(Title("Catalog")),
        "agent_version": TextField(Title("Agent version")),
    },
)

node_software_applications_docker = Node(
    name="software_applications_docker",
    path=["software", "applications", "docker"],
    title=Title("Docker"),
    attributes={
        "version": TextField(Title("Version")),
        "registry": TextField(Title("Registry")),
        "swarm_state": TextField(Title("Swarm state")),
        "swarm_node_id": TextField(Title("Swarm node ID")),
        "num_containers_total": NumberField(Title("#Containers"), render=UNIT_COUNT),
        "num_containers_running": NumberField(Title("#Containers running"), render=UNIT_COUNT),
        "num_containers_stopped": NumberField(Title("#Containers stopped"), render=UNIT_COUNT),
        "num_containers_paused": NumberField(Title("#Containers paused"), render=UNIT_COUNT),
        "num_images": NumberField(Title("#Images"), render=UNIT_COUNT),
    },
)

node_software_applications_docker_container = Node(
    name="software_applications_docker_container",
    path=["software", "applications", "docker", "container"],
    title=Title("Container"),
    attributes={
        "node_name": TextField(Title("Node name")),
    },
)

node_software_applications_docker_container_networks = Node(
    name="software_applications_docker_container_networks",
    path=["software", "applications", "docker", "container", "networks"],
    title=Title("Networks"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "ip_address": TextField(Title("IP address")),
            "ip_prefixlen": TextField(Title("IP prefix")),
            "gateway": TextField(Title("Gateway")),
            "mac_address": TextField(Title("MAC address")),
            "network_id": TextField(Title("Network ID")),
        },
    ),
)

node_software_applications_docker_container_ports = Node(
    name="software_applications_docker_container_ports",
    path=["software", "applications", "docker", "container", "ports"],
    title=Title("Ports"),
    table=Table(
        columns={
            "port": TextField(Title("Port")),
            "protocol": TextField(Title("Protocol")),
            "host_addresses": TextField(Title("Host addresses")),
        },
    ),
)

node_software_applications_docker_networks_containers = Node(
    name="software_applications_docker_networks_containers",
    path=["software", "applications", "docker", "networks", "containers"],
    title=Title("Network containers"),
    table=Table(
        columns={
            "network_id": TextField(Title("Network ID")),
            "id": TextField(Title("Container ID")),
            "name": TextField(Title("Name")),
            "ipv4_address": TextField(Title("IPv4 address")),
            "ipv6_address": TextField(Title("IPv6 address")),
            "mac_address": TextField(Title("MAC address")),
        },
    ),
)

node_software_applications_docker_node_labels = Node(
    name="software_applications_docker_node_labels",
    path=["software", "applications", "docker", "node_labels"],
    title=Title("Node labels"),
    table=Table(
        columns={
            "label": TextField(Title("Label")),
        },
    ),
)

node_software_applications_docker_swarm_manager = Node(
    name="software_applications_docker_swarm_manager",
    path=["software", "applications", "docker", "swarm_manager"],
    title=Title("Swarm managers"),
    table=Table(
        columns={
            "NodeID": TextField(Title("Node ID")),
            "Addr": TextField(Title("Address")),
        },
    ),
)

node_software_applications_fortinet = Node(
    name="software_applications_fortinet",
    path=["software", "applications", "fortinet"],
    title=Title("Fortinet"),
)

node_software_applications_fortinet_fortigate_high_availability = Node(
    name="software_applications_fortinet_fortigate_high_availability",
    path=["software", "applications", "fortinet", "fortigate_high_availability"],
    title=Title("FortiGate HighAvailability"),
)

node_software_applications_fortinet_fortisandbox = Node(
    name="software_applications_fortinet_fortisandbox",
    path=["software", "applications", "fortinet", "fortisandbox"],
    title=Title("FortiSandbox software"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
        },
    ),
)

node_software_applications_fritz = Node(
    name="software_applications_fritz",
    path=["software", "applications", "fritz"],
    title=Title("Fritz"),
    attributes={
        "link_type": TextField(Title("Link type")),
        "wan_access_type": TextField(Title("WAN access type")),
        "auto_disconnect_time": TextField(Title("Auto-disconnect time")),
        "dns_server_1": TextField(Title("DNS server 1")),
        "dns_server_2": TextField(Title("DNS server 2")),
        "voip_dns_server_1": TextField(Title("VoIP DNS server 1")),
        "voip_dns_server_2": TextField(Title("VoIP DNS server 2")),
        "upnp_config_enabled": TextField(Title("uPnP configuration enabled")),
    },
)

node_software_applications_ibm_mq = Node(
    name="software_applications_ibm_mq",
    path=["software", "applications", "ibm_mq"],
    title=Title("IBM MQ"),
    attributes={
        "managers": TextField(Title("Managers")),
        "channels": TextField(Title("Channels")),
        "queues": TextField(Title("Queues")),
    },
)

node_software_applications_ibm_mq_channels = Node(
    name="software_applications_ibm_mq_channels",
    path=["software", "applications", "ibm_mq", "channels"],
    title=Title("IBM MQ channels"),
    table=Table(
        view=View(name="invibmmqchannels", title=Title("IBM MQ channels")),
        columns={
            "qmgr": TextField(Title("Queue manager name")),
            "name": TextField(Title("Channel")),
            "type": TextField(Title("Type")),
            "status": TextField(Title("Status")),
            "monchl": TextField(Title("Monitoring")),
        },
    ),
)

node_software_applications_ibm_mq_managers = Node(
    name="software_applications_ibm_mq_managers",
    path=["software", "applications", "ibm_mq", "managers"],
    title=Title("IBM MQ managers"),
    table=Table(
        view=View(name="invibmmqmanagers", title=Title("IBM MQ managers")),
        columns={
            "name": TextField(Title("Queue manager name")),
            "instver": TextField(Title("Version")),
            "instname": TextField(Title("Installation")),
            "status": TextField(Title("Status")),
            "standby": TextField(Title("Standby")),
            "ha": TextField(Title("HA")),
        },
    ),
)

node_software_applications_ibm_mq_queues = Node(
    name="software_applications_ibm_mq_queues",
    path=["software", "applications", "ibm_mq", "queues"],
    title=Title("IBM MQ queues"),
    table=Table(
        view=View(name="invibmmqqueues", title=Title("IBM MQ queues")),
        columns={
            "qmgr": TextField(Title("Queue manager name")),
            "name": TextField(Title("Queue")),
            "maxdepth": TextField(Title("Max depth")),
            "maxmsgl": TextField(Title("Max length")),
            "created": TextField(Title("Created")),
            "altered": TextField(Title("Altered")),
            "monq": TextField(Title("Monitoring")),
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
        "kube_proxy_version": TextField(Title("Kube-proxy version")),
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

node_software_applications_mobileiron = Node(
    name="software_applications_mobileiron",
    path=["software", "applications", "mobileiron"],
    title=Title("Mobileiron"),
    attributes={
        "partition_name": TextField(Title("Partition name")),
        "registration_state": TextField(Title("Registration state")),
    },
)

node_software_applications_mssql = Node(
    name="software_applications_mssql",
    path=["software", "applications", "mssql"],
    title=Title("MSSQL"),
)

node_software_applications_oracle = Node(
    name="software_applications_oracle",
    path=["software", "applications", "oracle"],
    title=Title("Oracle DB"),
)

node_software_applications_oracle_dataguard_stats = Node(
    name="software_applications_oracle_dataguard_stats",
    path=["software", "applications", "oracle", "dataguard_stats"],
    title=Title("Oracle dataguard statistics"),
    table=Table(
        view=View(name="invoradataguardstats", title=Title("Oracle dataguard statistics")),
        columns={
            "sid": TextField(Title("SID")),
            "db_unique": TextField(Title("Name")),
            "role": TextField(Title("Role")),
            "switchover": TextField(Title("Switchover")),
        },
    ),
)

node_software_applications_oracle_instance = Node(
    name="software_applications_oracle_instance",
    path=["software", "applications", "oracle", "instance"],
    title=Title("Oracle instances"),
    table=Table(
        view=View(name="invorainstance", title=Title("Oracle instances")),
        columns={
            "sid": TextField(Title("SID")),
            "pname": TextField(Title("Process name")),
            "version": TextField(Title("Version")),
            "openmode": TextField(Title("Open mode")),
            "logmode": TextField(Title("Log mode")),
            "logins": TextField(Title("Logins")),
            "db_uptime": NumberField(Title("Uptime"), render=UNIT_AGE),
            "db_creation_time": TextField(Title("Creation time")),
        },
    ),
)

node_software_applications_oracle_pga = Node(
    name="software_applications_oracle_pga",
    path=["software", "applications", "oracle", "pga"],
    title=Title("Oracle PGA info"),
    table=Table(
        view=View(name="invorapga", title=Title("Oracle PGA info")),
        columns={
            "sid": TextField(Title("SID")),
            "aggregate_pga_auto_target": NumberField(
                Title("Aggregate PGA auto target"), render=UNIT_BYTES
            ),
            "aggregate_pga_target_parameter": NumberField(
                Title("Aggregate PGA target parameter"), render=UNIT_BYTES
            ),
            "bytes_processed": NumberField(Title("Bytes processed"), render=UNIT_BYTES),
            "extra_bytes_read_written": NumberField(
                Title("Extra bytes read/written"), render=UNIT_BYTES
            ),
            "global_memory_bound": NumberField(Title("Global memory bound"), render=UNIT_BYTES),
            "maximum_pga_allocated": NumberField(Title("Maximum PGA allocated"), render=UNIT_BYTES),
            "maximum_pga_used_for_auto_workareas": NumberField(
                Title("Maximum PGA used for auto workareas"), render=UNIT_BYTES
            ),
            "maximum_pga_used_for_manual_workareas": NumberField(
                Title("Maximum PGA used for manual workareas"), render=UNIT_BYTES
            ),
            "total_pga_allocated": NumberField(Title("Total PGA allocated"), render=UNIT_BYTES),
            "total_pga_inuse": NumberField(Title("Total PGA inuse"), render=UNIT_BYTES),
            "total_pga_used_for_auto_workareas": NumberField(
                Title("Total PGA used for auto workareas"), render=UNIT_BYTES
            ),
            "total_pga_used_for_manual_workareas": NumberField(
                Title("Total PGA used for manual workareas"), render=UNIT_BYTES
            ),
            "total_freeable_pga_memory": NumberField(
                Title("Total freeable PGA memory"), render=UNIT_BYTES
            ),
        },
    ),
)

node_software_applications_oracle_recovery_area = Node(
    name="software_applications_oracle_recovery_area",
    path=["software", "applications", "oracle", "recovery_area"],
    title=Title("Oracle recovery areas"),
    table=Table(
        view=View(name="invorarecoveryarea", title=Title("Oracle recovery areas")),
        columns={
            "sid": TextField(Title("SID")),
            "flashback": TextField(Title("Flashback")),
        },
    ),
)

node_software_applications_oracle_sga = Node(
    name="software_applications_oracle_sga",
    path=["software", "applications", "oracle", "sga"],
    title=Title("Oracle SGA info"),
    table=Table(
        view=View(name="invorasga", title=Title("Oracle SGA info")),
        columns={
            "sid": TextField(Title("SID")),
            "fixed_size": NumberField(Title("Fixed size"), render=UNIT_BYTES),
            "redo_buffer": NumberField(Title("Redo buffers"), render=UNIT_BYTES),
            "buf_cache_size": NumberField(Title("Buffer cache size"), render=UNIT_BYTES),
            "in_mem_area_size": NumberField(Title("In-memory area"), render=UNIT_BYTES),
            "shared_pool_size": NumberField(Title("Shared pool size"), render=UNIT_BYTES),
            "large_pool_size": NumberField(Title("Large pool size"), render=UNIT_BYTES),
            "java_pool_size": NumberField(Title("Java pool size"), render=UNIT_BYTES),
            "streams_pool_size": NumberField(Title("Streams pool size"), render=UNIT_BYTES),
            "shared_io_pool_size": NumberField(Title("Shared pool size"), render=UNIT_BYTES),
            "data_trans_cache_size": NumberField(
                Title("Data transfer cache size"), render=UNIT_BYTES
            ),
            "granule_size": NumberField(Title("Granule size"), render=UNIT_BYTES),
            "max_size": NumberField(Title("Maximum size"), render=UNIT_BYTES),
            "start_oh_shared_pool": NumberField(
                Title("Startup overhead in shared pool"), render=UNIT_BYTES
            ),
            "free_mem_avail": NumberField(Title("Free SGA memory available"), render=UNIT_BYTES),
        },
    ),
)

node_software_applications_oracle_systemparameter = Node(
    name="software_applications_oracle_systemparameter",
    path=["software", "applications", "oracle", "systemparameter"],
    title=Title("Oracle system parameters"),
    table=Table(
        view=View(name="invorasystemparameter", title=Title("Oracle system parameters")),
        columns={
            "sid": TextField(Title("SID")),
            "name": TextField(Title("Name")),
            "value": TextField(Title("Value")),
            "isdefault": TextField(Title("Is default")),
        },
    ),
)

node_software_applications_oracle_tablespaces = Node(
    name="software_applications_oracle_tablespaces",
    path=["software", "applications", "oracle", "tablespaces"],
    title=Title("Oracle tablespaces"),
    table=Table(
        view=View(name="invoratablespace", title=Title("Oracle tablespaces")),
        columns={
            "sid": TextField(Title("SID")),
            "name": TextField(Title("Name")),
            "version": TextField(Title("Version")),
            "type": TextField(Title("Type")),
            "autoextensible": TextField(Title("Autoextensible")),
            "current_size": NumberField(Title("Current size"), render=UNIT_BYTES),
            "max_size": NumberField(Title("Max. size"), render=UNIT_BYTES),
            "used_size": NumberField(Title("Used size"), render=UNIT_BYTES),
            "num_increments": TextField(Title("#Increments")),
            "increment_size": NumberField(Title("Increment size"), render=UNIT_BYTES),
            "free_space": NumberField(Title("Free space"), render=UNIT_BYTES),
        },
    ),
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

node_software_bios = Node(
    name="software_bios",
    path=["software", "bios"],
    title=Title("BIOS"),
    attributes={
        "vendor": TextField(Title("Vendor")),
        "version": TextField(Title("Version")),
        "date": NumberField(Title("Date"), render=_render_date),
    },
)

node_software_configuration = Node(
    name="software_configuration",
    path=["software", "configuration"],
    title=Title("Configuration"),
)

node_software_configuration_organisation = Node(
    name="software_configuration_organisation",
    path=["software", "configuration", "organisation"],
    title=Title("Organisation"),
    attributes={
        "organisation_id": TextField(Title("Organisation ID")),
        "organisation_name": TextField(Title("Organisation name")),
        "network_id": TextField(Title("Network ID")),
        "address": TextField(Title("Address")),
    },
)
