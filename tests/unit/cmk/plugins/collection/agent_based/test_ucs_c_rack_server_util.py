#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.collection.agent_based.ucs_c_rack_server_util import (
    check_ucs_c_rack_server_util,
    check_ucs_c_rack_server_util_cpu_,
    check_ucs_c_rack_server_util_mem,
    check_ucs_c_rack_server_util_pci_io,
    discover_ucs_c_rack_server_util,
    parse_ucs_c_rack_server_util,
    Section,
)


@pytest.fixture(name="section", scope="module")
def fixture_section() -> Section:
    return parse_ucs_c_rack_server_util(
        [
            [
                "serverUtilization",
                "dn sys/rack-unit-1/utilization",
                "overallUtilization 0",
                "cpuUtilization 0",
                "memoryUtilization 0",
                "ioUtilization 0",
            ],
            [
                "serverUtilization",
                "dn sys/rack-unit-2/utilization",
                "overallUtilization 91",
                "cpuUtilization 92",
                "memoryUtilization 93",
                "ioUtilization 94",
            ],
        ]
    )


def test_discover_ucs_c_rack_server_util(section: Section) -> None:
    assert list(discover_ucs_c_rack_server_util(section)) == [
        Service(item="Rack unit 1"),
        Service(item="Rack unit 2"),
    ]


@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "Rack unit 1",
            [
                Result(state=State.OK, summary="0%"),
                Metric("overall_util", 0.0, levels=(90.0, 95.0)),
            ],
            id="ok",
        ),
        pytest.param(
            "Rack unit 2",
            [
                Result(state=State.WARN, summary="91.00% (warn/crit at 90.00%/95.00%)"),
                Metric("overall_util", 91.0, levels=(90.0, 95.0)),
            ],
            id="warn",
        ),
    ],
)
def test_check_ucs_c_rack_server_util(
    section: Section,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_ucs_c_rack_server_util(
                item=item,
                params={"upper_levels": (90.0, 95.0)},
                section=section,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "Rack unit 1",
            [
                Result(state=State.OK, summary="Total CPU: 0%"),
                Metric("util", 0.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="ok",
        ),
        pytest.param(
            "Rack unit 2",
            [
                Result(state=State.WARN, summary="Total CPU: 92.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 92.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
            ],
            id="warn",
        ),
    ],
)
def test_check_ucs_c_rack_server_util_cpu(
    section: Section,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_ucs_c_rack_server_util_cpu_(
                item=item,
                params={"levels": (90.0, 95.0)},
                section=section,
                value_store={},
                timestamp=0,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "Rack unit 1",
            [
                Result(state=State.OK, summary="0%"),
                Metric("pci_io_util", 0.0, levels=(90.0, 95.0)),
            ],
            id="ok",
        ),
        pytest.param(
            "Rack unit 2",
            [
                Result(state=State.WARN, summary="94.00% (warn/crit at 90.00%/95.00%)"),
                Metric("pci_io_util", 94.0, levels=(90.0, 95.0)),
            ],
            id="warn",
        ),
    ],
)
def test_check_ucs_c_rack_server_util_pci_io(
    section: Section,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_ucs_c_rack_server_util_pci_io(
                item=item,
                params={"upper_levels": (90.0, 95.0)},
                section=section,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "Rack unit 1",
            [
                Result(state=State.OK, summary="0%"),
                Metric("memory_util", 0.0, levels=(90.0, 95.0)),
            ],
            id="ok",
        ),
        pytest.param(
            "Rack unit 2",
            [
                Result(state=State.WARN, summary="93.00% (warn/crit at 90.00%/95.00%)"),
                Metric("memory_util", 93.0, levels=(90.0, 95.0)),
            ],
            id="warn",
        ),
    ],
)
def test_check_ucs_c_rack_server_util_mem(
    section: Section,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_ucs_c_rack_server_util_mem(
                item=item,
                params={"upper_levels": (90.0, 95.0)},
                section=section,
            )
        )
        == expected_result
    )
