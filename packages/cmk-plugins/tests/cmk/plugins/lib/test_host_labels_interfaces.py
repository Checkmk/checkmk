#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import sys
from collections.abc import Iterable, Mapping
from ipaddress import (
    IPv4Interface,
    IPv6Interface,
)
from pathlib import Path

import pytest

from cmk.agent_based.v2 import (
    HostLabel,
    HostLabelGenerator,
)
from cmk.plugins.lib.host_labels_interfaces import host_labels_if


@pytest.mark.parametrize(
    ("section", "expected_result"),
    [
        pytest.param(
            {
                "eth0": [
                    IPv4Interface("10.86.60.1/27"),
                    IPv6Interface("fe80::200:5efe:515c:6232/64"),
                ],
                "eth1": [
                    IPv6Interface("fe80::200:5efe:515c:6232/64"),
                    IPv4Interface("12.12.12.1/3"),
                ],
            },
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
            id="host_labels_01_v4_multihomed",
        ),
        pytest.param(
            {
                "lo": [
                    IPv4Interface("127.0.0.1/8"),
                    IPv6Interface("::1/128"),
                ],
                "ens32": [
                    IPv4Interface("192.168.10.144/24"),
                    IPv6Interface("fe80::20c:29ff:fe82:fd72/64"),
                ],
            },
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
            ],
            id="host_labels_02_v4_singlehomed",
        ),
        pytest.param(
            {
                "lo": [
                    IPv4Interface("127.0.0.1/8"),
                    IPv6Interface("::1/128"),
                ],
                "enp0s31f6": [
                    IPv4Interface("95.216.118.249"),
                    IPv6Interface("2a01:4f9:2b:1c86::2/128"),  # note: different subnet than..
                    IPv6Interface("fe80::921b:eff:fefe:8a16/64"),
                ],
                "vmbr0": [
                    IPv4Interface("95.217.149.46/32"),
                    IPv6Interface("2a01:4f9:2b:1c86::2/64"),  #  .. this one -> multihomed for now
                    IPv6Interface("fe80::6871:a0ff:fefe:cd60/64"),
                ],
                "vmbr1": [
                    IPv6Interface("fe80::dcc3:a2ff:fe8b:acf7/64"),
                ],
                "veth300i0@if2": [],
                "fwbr300i0": [],
            },
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
                HostLabel("cmk/l3v6_topology", "multihomed"),
            ],
            id="host_labels_03",
        ),
        pytest.param(
            {
                "lo": [
                    IPv4Interface("127.0.0.1/8"),
                    IPv6Interface("::1/128"),
                ],
                "enp2s0": [
                    IPv6Interface("fe80::5a47:caff:fe78:3d59/64"),
                ],
                "enp3s0": [],
                "enp2s0.10@enp2s0": [],
                "vmbr0": [
                    IPv4Interface("192.168.1.13/24"),
                    IPv6Interface("fe80::5a47:caff:fe78:3d59/64"),
                ],
                "enp2s0.30@enp2s0": [],
                "vmbr1": [],
                "enp2s0.300@enp2s0": [],
            },
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
            ],
            id="host_labels_04",
        ),
        pytest.param(
            {
                "lo": [
                    IPv4Interface("127.0.0.1/8"),
                    IPv6Interface("::1/128"),
                ],
                "ens18": [
                    IPv4Interface("192.168.1.14/24"),
                    IPv6Interface("2a00:6666:4444:3333:2222:1111:1d90:a380/64"),
                    IPv6Interface("fe80::b570:2342:84a8:678/64"),
                ],
                "wls16": [
                    IPv4Interface("192.168.200.2/24"),
                    IPv6Interface("fe80::7406:4444:4444:6550/64"),
                ],
                "docker0": [
                    IPv4Interface("172.17.0.1/16"),
                    IPv6Interface("fe80::48bf:4444:4444:db67/64"),
                ],
                "hassio": [
                    IPv4Interface("172.30.32.1/23"),
                    IPv6Interface("fe80::a001:fff:4444:7ec6/64"),
                ],
                "br-7bddd354643c": [
                    IPv4Interface("172.18.0.1/16"),
                    IPv6Interface("fe80::9031:8dff:fec2:24f1/64"),
                ],
                "veth9e42229@if2": [
                    IPv6Interface("fe80::b09d:4aff:fe50:683b/64"),
                ],
                "veth40657ac@if2": [
                    IPv6Interface("fe80::d4d7:e9ff:fec6:4df8/64"),
                ],
                "vetha8ae1a1@if2": [
                    IPv6Interface("fe80::5c75:e0ff:fe54:2b7b/64"),
                ],
                "wpan0": [
                    # Adds some ULAs
                    IPv6Interface("fddf:d584:190e:49b5:0:ff:fe00:fc10/64"),
                    IPv6Interface("fd00:14dd:8bdc:1:b96b:d0e5:21e6:9eec/64"),
                    IPv6Interface("fddf:d584:190e:49b5:0:ff:fe00:8400/64"),
                    IPv6Interface("fddf:d584:190e:49b5:f50c:c53c:bb5:e652/64"),
                    IPv6Interface("fe80::8005:a23c:7a6f:4c3a/64"),
                ],
            },
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
                HostLabel("cmk/l3v6_topology", "singlehomed"),
            ],
            id="host_labels_05_ULA",
        ),
        pytest.param(
            {
                "lo": [
                    IPv4Interface("127.0.0.1/8"),
                    IPv6Interface("::1/128"),
                ],
                "eth0@if14": [
                    IPv4Interface("192.168.1.20/24"),
                    IPv6Interface("fe80::48f:17ff:fefc:2731/64"),
                ],
                "wg0": [
                    IPv4Interface("10.99.90.2/24"),
                ],
            },
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
            id="host_labels_06_regression_only",
        ),
        pytest.param(
            {
                "lo": [
                    IPv4Interface("127.0.0.1/8"),
                    IPv6Interface("::1/128"),
                ],
                "ens18": [
                    IPv4Interface("192.168.1.2/24"),
                    IPv6Interface("2a00:6666:4444:3333:222:3eff:fe0e:7d2b/64"),
                    IPv6Interface("fe80::216:3eff:fe0e:7d2b/64"),
                ],
                "ztr2qtmfyn": [
                    IPv4Interface("172.28.1.1/16"),
                    IPv6Interface("fe80::ca1c:baff:fe55:3b2f/64"),
                ],
                "ztmosjnylr": [
                    IPv4Interface("172.27.74.55/16"),
                    IPv6Interface("fe80::a820:a8ff:fea1:a3dd/64"),
                ],
                "tailscale0": [
                    IPv6Interface("fe80::dead:22ff:4223:6f57/64"),
                ],
            },
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
                HostLabel("cmk/l3v6_topology", "singlehomed"),
            ],
            id="host_labels_07_regression_only",
        ),
    ],
)
def test_host_labels_if(
    section: Mapping[str, Iterable[IPv4Interface | IPv6Interface]],
    expected_result: HostLabelGenerator,
) -> None:
    assert list(host_labels_if(section)) == list(expected_result)


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just set _PYTEST_RAISES=1 and run this file from your IDE and dive into the code.
    source_file_path = (
        (base := (test_file := Path(__file__)).parents[4])
        / test_file.parent.relative_to(base / "tests")
        / test_file.name[5:]
    ).as_posix()
    assert pytest.main(["--doctest-modules", source_file_path]) in {0, 5}
    pytest.main(["-vvsx", *sys.argv[1:], __file__])
