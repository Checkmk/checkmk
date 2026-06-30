#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    Node,
    NumberField,
    Table,
    TextField,
    Title,
    View,
)

node_software_applications_cisco_meraki = Node(
    name="software_applications_cisco_meraki",
    path=["software", "applications", "cisco_meraki"],
    title=Title("Cisco Meraki"),
)

node_software_applications_cisco_meraki_licenses = Node(
    name="software_applications_cisco_meraki_licenses",
    path=["software", "applications", "cisco_meraki", "licenses"],
    title=Title("Licenses"),
    table=Table(
        view=View(name="invmerakilicenses", title=Title("Licenses")),
        columns={
            "org_id": TextField(Title("Organization ID")),
            "org_name": TextField(Title("Organization name")),
            "summary": NumberField(Title("Summary")),
            "gateway_mg_count": NumberField(Title("Gateway (MG)")),
            "wireless_mr_count": NumberField(Title("Access points/Wireless (MR)")),
            "switch_ms_count": NumberField(Title("Switches (MS)")),
            "sensor_mt_count": NumberField(Title("Sensor (MT)")),
            "video_mv_count": NumberField(Title("Video (MV)")),
            "security_mx_count": NumberField(Title("Security/SD-WAN (MX)")),
            "systems_manager_sm_count": NumberField(Title("Systems manager (SM)")),
            "other_count": NumberField(Title("Other")),
        },
    ),
)

node_software_applications_cisco_meraki_networks = Node(
    name="software_applications_cisco_meraki_networks",
    path=["software", "applications", "cisco_meraki", "networks"],
    title=Title("Networks"),
    table=Table(
        view=View(name="invmerakinetworks", title=Title("Networks")),
        columns={
            "org_id": TextField(Title("Organization ID")),
            "org_name": TextField(Title("Organization name")),
            "network_id": TextField(Title("Network ID")),
            "network_name": TextField(Title("Network name")),
            "time_zone": TextField(Title("Time zone")),
            "product_types": TextField(Title("Product types")),
            "tags": TextField(Title("Tags")),
            "notes": TextField(Title("Notes")),
            "enrollment_string": TextField(Title("Enrollment string")),
            "is_bound_to_template": TextField(Title("Is bound to template")),
            "url": TextField(Title("URL")),
        },
    ),
)

node_software_applications_cisco_meraki_organisations = Node(
    name="software_applications_cisco_meraki_organisations",
    path=["software", "applications", "cisco_meraki", "organisations"],
    title=Title("Organizations"),
    table=Table(
        view=View(name="invmerakiorganisations", title=Title("Organizations")),
        columns={
            "org_id": TextField(Title("Organization ID")),
            "org_name": TextField(Title("Organization name")),
            "api_status": TextField(Title("API status")),
            "licensing_model": TextField(Title("Licensing model")),
            "cloud_region": TextField(Title("Cloud region")),
            "url": TextField(Title("URL")),
        },
    ),
)

node_software_configuration_organisation = Node(
    name="software_configuration_organisation",
    path=["software", "configuration", "organisation"],
    title=Title("Organization"),
    attributes={
        "organisation_id": TextField(Title("Organization ID")),
        "organisation_name": TextField(Title("Organization name")),
        "network_id": TextField(Title("Network ID")),
        "network_name": TextField(Title("Network name")),
        "address": TextField(Title("Address")),
    },
)
