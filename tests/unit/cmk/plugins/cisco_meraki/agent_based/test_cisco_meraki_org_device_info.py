#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Attributes, HostLabel
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_device_info import (
    host_label_meraki_device_info,
    inventory_device_info,
    parse_device_info,
)
from cmk.plugins.cisco_meraki.lib.schema import Device


class _DeviceFactory(TypedDictFactory[Device]):
    __check_model__ = False


def test_host_label_meraki_device_info() -> None:
    device = _DeviceFactory.build(
        name="My AP",
        productType="appliance",
        organisation_id="123",
        organisation_name="org-name",
        networkId="N_24329156",
        networkName="work",
    )
    string_table = [[f"[{json.dumps(device)}]"]]
    section = parse_device_info(string_table)
    assert section

    value = list(host_label_meraki_device_info(section))
    expected = [
        HostLabel("cmk/meraki", "yes"),
        HostLabel("cmk/meraki/device_type", "appliance"),
        HostLabel("cmk/meraki/net_id", "N_24329156"),
        HostLabel("cmk/meraki/net_name", "work"),
        HostLabel("cmk/meraki/org_id", "123"),
        HostLabel("cmk/meraki/org_name", "org-name"),
    ]

    assert value == expected


def test_inventory_device_info() -> None:
    device = _DeviceFactory.build(
        name="My AP",
        serial="Q234-ABCD-5678",
        productType="appliance",
        model="MR34",
        mac="00:11:22:33:44:55",
        firmware="wireless-25-14",
        organisation_id="123",
        organisation_name="org-name",
        networkId="N_24329156",
        networkName="work",
        address="1600 Pennsylvania Ave",
    )
    string_table = [[f"[{json.dumps(device)}]"]]
    section = parse_device_info(string_table)
    assert section

    value = list(inventory_device_info(section))
    expected = [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "product": "appliance",
                "serial": "Q234-ABCD-5678",
                "model": "MR34",
                "description": "My AP",
                "mac_address": "00:11:22:33:44:55",
                "manufacturer": "Cisco Meraki",
            },
        ),
        Attributes(
            path=["software", "firmware"],
            inventory_attributes={
                "version": "wireless-25-14",
            },
        ),
        Attributes(
            path=["software", "configuration", "organisation"],
            inventory_attributes={
                "organisation_id": "123",
                "organisation_name": "org-name",
                "network_id": "N_24329156",
                "network_name": "work",
                "address": "1600 Pennsylvania Ave",
            },
        ),
    ]
    assert value == expected
