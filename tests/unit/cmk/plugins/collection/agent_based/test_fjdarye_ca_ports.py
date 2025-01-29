#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.fjdarye_ca_ports import (
    check_fjdarye_ca_ports,
    discover_fjdarye_ca_ports,
    parse_fjdarye_ca_ports,
)


@pytest.mark.parametrize(
    "string_table, parse_result",
    [
        pytest.param(
            [
                [["0", "11", "0", "0", "0", "0"], ["1", "11", "0", "0", "0", "0"]],
                [],
            ],
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "1": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            id="The input is parsed into a dictionary that contains information about the index, mode, read IOs, read throughput, write IOs and write throughput of the disk.",
        ),
        pytest.param(
            [],
            {},
            id="If the input is empty, nothing is parsed",
        ),
    ],
)
def test_parse_fjdarye_ca_ports(
    string_table: Sequence[StringTable],
    parse_result: Mapping[str, Mapping[str, float | str]],
) -> None:
    assert parse_fjdarye_ca_ports(string_table) == parse_result


@pytest.mark.parametrize(
    # The default parameters don't work when testing
    "section, params, discovery_result",
    [
        pytest.param(
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "1": {
                    "mode": "CARA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "2": {
                    "mode": "RA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            {"indices": [], "modes": ["CA", "CARA"]},
            [(Service(item="0")), Service(item="1")],
            id="If the discovery ruleset is not configured, disks in default modes ('CA' and 'CARA') are discovered.",
        ),
        pytest.param(
            {
                "0": {
                    "mode": "BA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "1": {
                    "mode": "AA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            {"indices": [], "modes": []},
            [(Service(item="0")), Service(item="1")],
            id="If the modes and indices in the discovery ruleset are configured as an empty list, all disks are discovered.",
        ),
        pytest.param(
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "1": {
                    "mode": "CARA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            {"modes": ["CA"], "indices": []},
            [Service(item="0")],
            id="If the mode is configured in the discovery ruleset, only the disks with the configured mode are discovered.",
        ),
        pytest.param(
            {
                "231": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "232": {
                    "mode": "AA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "233": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            {
                "indices": [
                    "231",
                    "232",
                ],
                "modes": ["CA", "CARA"],
            },
            [Service(item="231")],
            id="If only the indices are configured in the discovery ruleset, only disks with these indices and in default modes ('CA' and 'CARA') are discovered.",
        ),
        pytest.param(
            {
                "231": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "232": {
                    "mode": "AA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "233": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            {
                "indices": [
                    "231",
                    "232",
                ],
                "modes": [],
            },
            [Service(item="231"), Service(item="232")],
            id="If the indices are configured and the modes are configured to an empty list, only the disks with the given indices are discovered.",
        ),
        pytest.param(
            {
                "231": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "232": {
                    "mode": "AA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
                "233": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            {
                "indices": [
                    "231",
                    "232",
                ],
                "modes": ["CA"],
            },
            [Service(item="231")],
            id="If both the indices and the modes are configured, only the disks that match both criterias are discovered.",
        ),
    ],
)
def test_discover_fjdarye_ca_ports(
    section: Mapping[str, Mapping[str, float | str]],
    params: Mapping[str, Sequence[str]],
    discovery_result: Sequence[Service],
) -> None:
    assert list(discover_fjdarye_ca_ports(section=section, params=params)) == discovery_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "item, section, check_result_showing_mode",
    [
        pytest.param(
            "0",
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            Result(state=State.OK, summary="Mode: CA"),
            id="If the item is found, the check result is OK and the mode is displayed.",
        ),
    ],
)
def test_check_fjdarye_ca_ports(
    item: str,
    section: Mapping[str, Mapping[str, float | str]],
    check_result_showing_mode: Result,
) -> None:
    check_result = list(check_fjdarye_ca_ports(item=item, params={}, section=section))
    assert check_result[0] == check_result_showing_mode


@pytest.mark.parametrize(
    "item, section, expected_check_result",
    [
        pytest.param(
            "1",
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0.0,
                    "read_throughput": 0.0,
                    "write_ios": 0.0,
                    "write_throughput": 0.0,
                },
            },
            [],
            id="If the item is not found, no check result is returned.",
        ),
    ],
)
def test_check_fjdarye_ca_ports_with_empty_input(
    item: str,
    section: Mapping[str, Mapping[str, float | str]],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(check_fjdarye_ca_ports(item=item, params={}, section=section)) == expected_check_result
    )
