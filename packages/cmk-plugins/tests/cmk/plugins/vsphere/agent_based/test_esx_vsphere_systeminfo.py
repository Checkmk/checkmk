#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Attributes, HostLabel
from cmk.plugins.vsphere.agent_based.esx_vsphere_systeminfo import (
    host_label_esx_vshpere_systeminfo,
    inventorize_esx_systeminfo,
    parse_esx_vsphere_systeminfo,
)

STRING_TABLE = [
    ["vendor", "VMware,", "Inc."],
    ["name", "VMware", "ESXi"],
    ["version", "8.0.2"],
    ["build", "22380479"],
    ["osType", "vmnix-x86"],
    ["propertyCollector", "ha-property-collector"],
]


def test_multi_word_values_are_joined_back_together() -> None:
    section = parse_esx_vsphere_systeminfo(STRING_TABLE)

    assert section["vendor"] == "VMware, Inc."
    assert section["name"] == "VMware ESXi"


def test_vcenter_is_labelled_as_vcenter() -> None:
    labels = list(host_label_esx_vshpere_systeminfo({"name": "VMware vCenter Server"}))

    assert labels == [HostLabel("cmk/vsphere_vcenter", "yes")]


def test_esxi_host_is_labelled_as_server() -> None:
    labels = list(host_label_esx_vshpere_systeminfo({"name": "VMware ESXi"}))

    assert labels == [HostLabel("cmk/vsphere_object", "server")]


def test_other_products_get_no_labels() -> None:
    assert list(host_label_esx_vshpere_systeminfo({"name": "VMware Workstation"})) == []


def test_missing_product_name_gets_no_labels() -> None:
    assert list(host_label_esx_vshpere_systeminfo({})) == []


def test_system_info_is_inventorised_as_operating_system() -> None:
    (attributes,) = inventorize_esx_systeminfo(parse_esx_vsphere_systeminfo(STRING_TABLE))

    assert isinstance(attributes, Attributes)
    assert attributes.path == ["software", "os"]
    assert attributes.inventory_attributes == {
        "arch": "x86_64",
        "vendor": "VMware, Inc.",
        "build": "22380479",
        "name": "VMware ESXi",
        "version": "8.0.2",
        "type": "vmnix-x86",
    }


def test_missing_system_info_fields_are_left_out_of_the_inventory() -> None:
    (attributes,) = inventorize_esx_systeminfo({"name": "VMware ESXi"})

    assert isinstance(attributes, Attributes)
    assert attributes.inventory_attributes == {"arch": "x86_64", "name": "VMware ESXi"}
