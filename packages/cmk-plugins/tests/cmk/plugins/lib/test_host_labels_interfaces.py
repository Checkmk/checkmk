#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Iterable
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
            (
                IPv4Interface("10.86.60.1/27"),
                IPv6Interface("fe80::200:5efe:515c:6232/64"),
                IPv4Interface("12.12.12.1/3"),
            ),
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
                HostLabel("cmk/l3v4_topology", "multihomed"),
            ],
        ),
        (
            [
                # "lo"
                IPv4Interface("127.0.0.1/8"),
                IPv6Interface("::1/128"),
                # "ens32"
                IPv4Interface("192.168.10.144/24"),
                IPv6Interface("fe80::20c:29ff:fe82:fd72/64"),
            ],
            [
                HostLabel("cmk/l3v4_topology", "singlehomed"),
            ],
        ),
    ],
)
def test_host_labels_if(
    section: Iterable[IPv4Interface | IPv6Interface],
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
