#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import (
    BoolField,
    DecimalNotation,
    Node,
    NumberField,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))

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
