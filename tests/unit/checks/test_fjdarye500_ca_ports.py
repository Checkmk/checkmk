#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.config
import cmk.base.plugin_contexts
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, parse_result",
    [
        pytest.param(
            [[["0", "11", "0", "0", "0", "0"], ["1", "11", "0", "0", "0", "0"]]],
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "1": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
            },
            id="The input is parsed into a dictionary that contains information about the index, mode, read IOs, read throughput, write IOs and write throughput of the disk.",
        ),
        pytest.param(
            [],
            None,
            id="If the input is empty, nothing is parsed",
        ),
    ],
)
def test_parse_fjdarye500_ca_ports(
    info: StringTable,
    parse_result: Mapping[str, Mapping[str, int | str]],
    fix_register: FixRegister,
) -> None:
    check = fix_register.snmp_sections[SectionName("fjdarye500_ca_ports")]
    assert check.parse_function(info) == parse_result


@pytest.mark.parametrize(
    "info, params, inventory_result",
    [
        pytest.param(
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "1": {
                    "mode": "CARA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "2": {
                    "mode": "RA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
            },
            {},
            [(Service(item="0")), Service(item="1")],
            id="If the discovery ruleset is not configured, disks in default modes ('CA' and 'CARA') are discovered.",
        ),
        pytest.param(
            {
                "0": {
                    "mode": "BA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "1": {
                    "mode": "AA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
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
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "1": {
                    "mode": "CARA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
            },
            {"modes": ["CA"]},
            [Service(item="0")],
            id="If the mode is configured in the discovery ruleset, only the disks with the configured mode are discovered.",
        ),
        pytest.param(
            {
                "231": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "232": {
                    "mode": "AA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "233": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
            },
            {
                "indices": [
                    "231",
                    "232",
                ]
            },
            [Service(item="231")],
            id="If only the indices are configured in the discovery ruleset, only disks with these indices and in default modes ('CA' and 'CARA') are discovered.",
        ),
        pytest.param(
            {
                "231": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "232": {
                    "mode": "AA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "233": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
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
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "232": {
                    "mode": "AA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
                "233": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
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
def test_inventory_fjdarye500_ca_ports(
    monkeypatch,
    info: Mapping[str, Mapping[str, int | str]],
    params: Mapping[str, Sequence[str]],
    inventory_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    monkeypatch.setattr(cmk.base.plugin_contexts, "_hostname", "foo")
    monkeypatch.setattr(
        cmk.base.config.ConfigCache, "host_extra_conf_merged", lambda s, h, r: params
    )

    check = fix_register.check_plugins[CheckPluginName("fjdarye500_ca_ports")]
    assert list(check.discovery_function(info)) == inventory_result


@pytest.mark.parametrize(
    "item, section, check_result",
    [
        pytest.param(
            "0",
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
            },
            [
                Result(state=State.OK, summary="Mode: CA"),
                Result(state=State.OK, summary="Read: 0.00 B/s"),
                Metric("disk_read_throughput", 0.0),
                Result(state=State.OK, summary="Write: 0.00 B/s"),
                Metric("disk_write_throughput", 0.0),
                Result(state=State.OK, summary="Read operations: 0.00 1/s"),
                Metric("disk_read_ios", 0.0),
                Result(state=State.OK, summary="Write operations: 0.00 1/s"),
                Metric("disk_write_ios", 0.0),
            ],
            id="If the item is found, the check shows the disk's mode in addition to information on disk performance.",
        ),
        pytest.param(
            "1",
            {
                "0": {
                    "mode": "CA",
                    "read_ios": 0,
                    "read_throughput": 0,
                    "write_ios": 0,
                    "write_throughput": 0,
                },
            },
            [],
            id="If the item is not found, no check result is returned.",
        ),
    ],
)
def test_check_fjdarye500_ca_ports(
    item: str,
    section: Mapping[str, Mapping[str, int | str]],
    check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("fjdarye500_ca_ports")]
    assert list(check.check_function(item=item, params={}, section=section)) == check_result
