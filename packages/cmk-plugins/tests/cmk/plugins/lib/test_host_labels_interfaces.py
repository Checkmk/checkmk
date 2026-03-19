#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

from cmk.agent_based.v2 import (
    HostLabel,
    HostLabelGenerator,
)
from cmk.plugins.lib.host_labels_interfaces import host_labels_if
from cmk.plugins.lib.interfaces import (
    AugmentedIPv4Interface,
    AugmentedIPv6Interface,
    IPNetworkAdapter,
)


@pytest.mark.parametrize(
    ("section", "expected_result"),
    [
        pytest.param(
            [
                IPNetworkAdapter(
                    name="eth0",
                    inet4=[AugmentedIPv4Interface("10.86.60.1/24")],
                    inet6=[AugmentedIPv6Interface("fe80::200:5efe:515c:6232/64")],
                ),
                IPNetworkAdapter(
                    name="eth1",
                    inet4=[AugmentedIPv4Interface("12.12.12.1/24")],
                    inet6=[AugmentedIPv6Interface("fe80::200:5efe:515c:6232/64")],
                ),
            ],
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
            id="host_labels_01_v4_multihomed",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
                IPNetworkAdapter(
                    name="ens32",
                    inet4=[AugmentedIPv4Interface("192.168.10.144/24")],
                    inet6=[AugmentedIPv6Interface("fe80::20c:29ff:fe82:fd72/64")],
                ),
            ],
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
            ],
            id="host_labels_02_v4_singlehomed",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
                IPNetworkAdapter(
                    name="enp0s31f6",
                    inet4=[AugmentedIPv4Interface("95.216.118.249")],
                    inet6=[
                        AugmentedIPv6Interface("2a01:4f9:2b:1c86::2/128"),
                        AugmentedIPv6Interface("fe80::921b:eff:fefe:8a16/64"),
                    ],
                ),
                IPNetworkAdapter(
                    name="vmbr0",
                    inet4=[AugmentedIPv4Interface("95.217.149.46/32")],
                    inet6=[
                        AugmentedIPv6Interface("2a01:4f9:2b:1c86::2/64"),
                        AugmentedIPv6Interface("fe80::6871:a0ff:fefe:cd60/64"),
                    ],
                ),
                IPNetworkAdapter(
                    name="vmbr1",
                    inet6=[AugmentedIPv6Interface("fe80::dcc3:a2ff:fe8b:acf7/64")],
                ),
                IPNetworkAdapter(
                    name="veth300i0@if2",
                ),
                IPNetworkAdapter(
                    name="fwbr300i0",
                ),
            ],
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
                HostLabel("cmk/l3v6_topology", "singlehomed"),
            ],
            id="host_labels_03",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
                IPNetworkAdapter(
                    name="enp2s0",
                    inet6=[AugmentedIPv6Interface("fe80::5a47:caff:fe78:3d59/64")],
                ),
                IPNetworkAdapter(name="enp3s0"),
                IPNetworkAdapter(name="enp2s0.10@enp2s0"),
                IPNetworkAdapter(
                    name="vmbr0",
                    inet4=[AugmentedIPv4Interface("192.168.1.13/24")],
                    inet6=[AugmentedIPv6Interface("fe80::5a47:caff:fe78:3d59/64")],
                ),
                IPNetworkAdapter(name="enp2s0.30@enp2s0"),
                IPNetworkAdapter(name="vmbr1"),
                IPNetworkAdapter(name="enp2s0.300@enp2s0"),
            ],
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
            ],
            id="host_labels_04",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
                IPNetworkAdapter(
                    name="ens18",
                    inet4=[AugmentedIPv4Interface("192.168.1.14/24")],
                    inet6=[
                        AugmentedIPv6Interface("2a00:6666:4444:3333:2222:1111:1d90:a380/64"),
                        AugmentedIPv6Interface("fe80::b570:2342:84a8:678/64"),
                    ],
                ),
                IPNetworkAdapter(
                    name="wls16",
                    inet4=[AugmentedIPv4Interface("192.168.200.2/24")],
                    inet6=[AugmentedIPv6Interface("fe80::7406:4444:4444:6550/64")],
                ),
                IPNetworkAdapter(
                    name="docker0",
                    inet4=[AugmentedIPv4Interface("172.17.0.1/16")],
                    inet6=[AugmentedIPv6Interface("fe80::48bf:4444:4444:db67/64")],
                ),
                IPNetworkAdapter(
                    name="hassio",
                    inet4=[AugmentedIPv4Interface("172.30.32.1/23")],
                    inet6=[AugmentedIPv6Interface("fe80::a001:fff:4444:7ec6/64")],
                ),
                IPNetworkAdapter(
                    name="br-7bddd354643c",
                    inet4=[AugmentedIPv4Interface("172.18.0.1/16")],
                    inet6=[AugmentedIPv6Interface("fe80::9031:8dff:fec2:24f1/64")],
                ),
                IPNetworkAdapter(
                    name="veth9e42229@if2",
                    inet6=[AugmentedIPv6Interface("fe80::b09d:4aff:fe50:683b/64")],
                ),
                IPNetworkAdapter(
                    name="veth40657ac@if2",
                    inet6=[AugmentedIPv6Interface("fe80::d4d7:e9ff:fec6:4df8/64")],
                ),
                IPNetworkAdapter(
                    name="vetha8ae1a1@if2",
                    inet6=[AugmentedIPv6Interface("fe80::5c75:e0ff:fe54:2b7b/64")],
                ),
                # adds some ULAs
                IPNetworkAdapter(
                    name="wpan0",
                    inet6=[
                        AugmentedIPv6Interface("fddf:d584:190e:49b5:0:ff:fe00:fc10/64"),
                        AugmentedIPv6Interface("fd00:14dd:8bdc:1:b96b:d0e5:21e6:9eec/64"),
                        AugmentedIPv6Interface("fddf:d584:190e:49b5:0:ff:fe00:8400/64"),
                        AugmentedIPv6Interface("fddf:d584:190e:49b5:f50c:c53c:bb5:e652/64"),
                        AugmentedIPv6Interface("fe80::8005:a23c:7a6f:4c3a/64"),
                    ],
                ),
            ],
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
                HostLabel("cmk/l3v6_topology", "singlehomed"),
            ],
            id="host_labels_05_ULA",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
                IPNetworkAdapter(
                    name="eth0@if14",
                    inet4=[AugmentedIPv4Interface("192.168.1.20/24")],
                    inet6=[AugmentedIPv6Interface("fe80::48f:17ff:fefc:2731/64")],
                ),
                IPNetworkAdapter(
                    name="wg0",
                    inet4=[AugmentedIPv4Interface("10.99.90.2/24")],
                ),
            ],
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
            id="host_labels_06_regression_only",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
                IPNetworkAdapter(
                    name="ens18",
                    inet4=[AugmentedIPv4Interface("192.168.1.2/24")],
                    inet6=[
                        AugmentedIPv6Interface("2a00:6666:4444:3333:222:3eff:fe0e:7d2b/64"),
                        AugmentedIPv6Interface("fe80::216:3eff:fe0e:7d2b/64"),
                    ],
                ),
                IPNetworkAdapter(
                    name="ztr2qtmfyn",
                    inet4=[AugmentedIPv4Interface("172.28.1.1/16")],
                    inet6=[AugmentedIPv6Interface("fe80::ca1c:baff:fe55:3b2f/64")],
                ),
                IPNetworkAdapter(
                    name="ztmosjnylr",
                    inet4=[AugmentedIPv4Interface("172.27.74.55/16")],
                    inet6=[AugmentedIPv6Interface("fe80::a820:a8ff:fea1:a3dd/64")],
                ),
                IPNetworkAdapter(
                    name="tailscale0",
                    inet6=[AugmentedIPv6Interface("fe80::dead:22ff:4223:6f57/64")],
                ),
            ],
            [
                HostLabel("cmk/l3v4_topology", "multihomed"),
                HostLabel("cmk/l3v6_topology", "singlehomed"),
            ],
            id="host_labels_07_regression_only",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="lo",
                    inet4=[AugmentedIPv4Interface("127.0.0.1/8")],
                    inet6=[AugmentedIPv6Interface("::1/128")],
                ),
                IPNetworkAdapter(
                    name="eth0",
                    inet4=[AugmentedIPv4Interface("169.254.10.5/16")],
                    inet6=[AugmentedIPv6Interface("fe80::1/64")],
                ),
            ],
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
            ],
            id="host_labels_09_apipa_not_filtered",
        ),
        pytest.param(
            [
                IPNetworkAdapter(
                    name="one",
                    inet6=[AugmentedIPv6Interface("2a00:6020:4083:1100:333:1111:2222:3333/64")],
                ),
                IPNetworkAdapter(
                    name="two",
                    inet6=[AugmentedIPv6Interface("2a00:6020:4083:1101:333:1111:2222:3333/64")],
                ),
                IPNetworkAdapter(
                    name="three",
                    inet6=[AugmentedIPv6Interface("2a00:6020:4083:1102:333:1111:2222:3333/64")],
                ),
                IPNetworkAdapter(
                    name="four",
                    inet6=[AugmentedIPv6Interface("2a00:6020:4083:1103:333:1111:2222:3333/64")],
                ),
            ],
            [
                HostLabel("cmk/l3v6_topology", "multihomed"),
            ],
            id="host_labels_08_ipv6_subnets",
        ),
    ],
)
def test_host_labels_if(
    section: Iterable[IPNetworkAdapter],
    expected_result: HostLabelGenerator,
    request: pytest.FixtureRequest,
) -> None:
    assert list(host_labels_if(section)) == list(expected_result), (
        f"in param {request.node.callspec.id}"
    )


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
