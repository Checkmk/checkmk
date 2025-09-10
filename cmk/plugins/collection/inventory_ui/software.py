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
