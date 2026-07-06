#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

import pytest

from cmk.agent_based.v2 import HostLabel
from cmk.plugins.lib.device_types import get_device_type_label


@dataclass(frozen=True)
class _Section:
    description: str


@pytest.mark.parametrize(
    ("description", "expected_label"),
    [
        pytest.param(
            "Aruba JL658A 6300M 48SFP56 ... Switch PL.10.06.0010",
            HostLabel("cmk/device_type", "switch"),
            id="aruba legacy sysdescr with literal Switch",
        ),
        pytest.param(
            "Aruba JL658A 6300M 48SFP56 139W Swch PL.10.16.1040",
            HostLabel("cmk/device_type", "switch"),
            id="aruba new firmware sysdescr with abbreviated Swch",
        ),
        pytest.param(
            "Cisco Nexus MDS 9000 FC Switch",
            HostLabel("cmk/device_type", "fcswitch"),
            id="fibrechannel switch",
        ),
        pytest.param(
            "Palo Alto Networks Firewall PA-220",
            HostLabel("cmk/device_type", "firewall"),
            id="firewall",
        ),
    ],
)
def test_get_device_type_label(description: str, expected_label: HostLabel) -> None:
    assert list(get_device_type_label(_Section(description))) == [expected_label]


def test_get_device_type_label_no_match() -> None:
    assert list(get_device_type_label(_Section("Some generic SNMP device"))) == []
