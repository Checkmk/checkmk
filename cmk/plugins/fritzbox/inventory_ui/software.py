#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Node, TextField, Title

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
