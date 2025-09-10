#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import Node, Table, TextField, Title

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
