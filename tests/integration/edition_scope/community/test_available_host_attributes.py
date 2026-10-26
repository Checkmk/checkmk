#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.host_attributes import host_attribute_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_host_attributes() -> None:
    assert sorted(host_attribute_registry) == [
        "additional_ipv4addresses",
        "additional_ipv6addresses",
        "alias",
        "contactgroups",
        "inventory_failed",
        "ipaddress",
        "ipv6address",
        "labels",
        "locked_attributes",
        "locked_by",
        "management_address",
        "management_ipmi_credentials",
        "management_protocol",
        "management_snmp_community",
        "meta_data",
        "network_scan",
        "network_scan_result",
        "parents",
        "relations",
        "site",
        "snmp_community",
        "waiting_for_discovery",
    ]
