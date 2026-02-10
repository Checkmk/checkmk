#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

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
    "section, expected_result",
    [
        (
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
        ),
        (
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
        ),
        (
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
        ),
        (
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
        / test_file.name.lstrip("test_")
    ).as_posix()
    assert pytest.main(["--doctest-modules", source_file_path]) in {0, 5}
    pytest.main(["-vvsx", __file__])
