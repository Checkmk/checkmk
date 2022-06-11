#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Final

import pytest

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="inventory_lnx_distro", scope="module")
def _get_inventory_lnx_distro(fix_register) -> Callable:
    plugin = fix_register.inventory_plugins[InventoryPluginName("lnx_distro")]
    return lambda s: plugin.inventory_function(section=s)


def parse_lnx_distro(string_table):
    return string_table


STRING_TABLE_RH_OLD: Final = [
    [
        "/etc/redhat-release",
        "Red Hat Enterprise Linux Server release 6.4 (Santiago)",
    ],
]

STRING_TABLE_ORACLE_OLD: Final = [
    ["/etc/oracle-release", "Oracle LinuxServer release 7.1"],
]

STRING_TABLE_SUSE: Final = [
    [
        "/etc/lsb-release",
        (
            'LSB_VERSION="core-2.0-noarch:core-3.2-noarch:core-4.0-noarch:'
            'core-2.0-x86_64:core-3.2-x86_64:core-4.0-x86_64"'
        ),
    ],
    [
        "/etc/SuSE-release",
        "SUSE Linux Enterprise Server 11 (x86_64)",
        "VERSION = 11",
        "PATCHLEVEL = 3",
    ],
]

STRING_TABLE_NEW: Final = [
    ["[[[/etc/debian_version]]]"],
    ["bullseye/sid"],
    ["[[[/etc/lsb-release]]]"],
    [
        "DISTRIB_ID=Ubuntu",
        "DISTRIB_RELEASE=20.04",
        "DISTRIB_CODENAME=focal",
        'DISTRIB_DESCRIPTION="Ubuntu 20.04.3 LTS"',
    ],
    ["[[[/etc/os-release]]]"],
    [
        'NAME="Ubuntu"',
        'VERSION="20.04.3 LTS (Focal Fossa)"',
        "ID=ubuntu",
        "ID_LIKE=debian",
        'PRETTY_NAME="Ubuntu 20.04.3 LTS"',
        'VERSION_ID="20.04"',
        'HOME_URL="https://www.ubuntu.com/"',
        'SUPPORT_URL="https://help.ubuntu.com/"',
        'BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"',
        'PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"',
        "VERSION_CODENAME=focal",
        "UBUNTU_CODENAME=focal",
    ],
]


def test_inventory_lnx_distro_rh_old(inventory_lnx_distro) -> None:
    assert list(inventory_lnx_distro(parse_lnx_distro(STRING_TABLE_RH_OLD))) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": "Linux",
                "code_name": "Santiago",
                "vendor": "Red Hat",
                "version": "6.4",
                "name": "Red Hat Enterprise Linux Server release 6.4",
            },
        ),
    ]


def test_inventory_lnx_distro_oracle(inventory_lnx_distro) -> None:
    assert list(inventory_lnx_distro(parse_lnx_distro(STRING_TABLE_ORACLE_OLD))) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": "Linux",
                "vendor": "Oracle",
                "version": "7.1",
                "name": "LinuxServer",
            },
        ),
    ]


def test_inventory_lnx_distro_suse(inventory_lnx_distro) -> None:
    assert list(inventory_lnx_distro(parse_lnx_distro(STRING_TABLE_SUSE))) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": "Linux",
                "vendor": "SuSE",
                "version": "11.3",
                "name": "SUSE Linux Enterprise Server 11.3",
                "code_name": "Teal",
            },
        ),
    ]


def test_inventory_lnx_distro_new(inventory_lnx_distro) -> None:
    assert list(inventory_lnx_distro(parse_lnx_distro(STRING_TABLE_NEW))) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": "Linux",
                "vendor": "Ubuntu",
                "name": "Ubuntu 20.04.3 LTS",
                "version": "20.04",
                "code_name": "Focal",
            },
        ),
    ]
