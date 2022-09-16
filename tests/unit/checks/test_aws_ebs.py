#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

STRING_TABLE = [
    [
        '[{"Id":',
        '"id_10_VolumeReadOps",',
        '"Label":',
        '"123",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[[0.0030055,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_10_VolumeWriteOps",',
        '"Label":',
        '"123",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[[0.0030055,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_10_VolumeReadBytes",',
        '"Label":',
        '"123",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[[0.0030055,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_10_VolumeWriteBytes",',
        '"Label":',
        '"123",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[[0.0030055,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_10_VolumeQueueLength",',
        '"Label":',
        '"123",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[[0.0030055,",
        "null]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_10_BurstBalance",',
        '"Label":',
        '"123",',
        '"Timestamps":',
        "[],",
        '"Values":',
        "[[0.0030055,",
        "null]],",
        '"StatusCode":',
        '"Complete"}',
        "]",
    ]
]


@pytest.mark.parametrize(
    "string_table, discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service(item="123")],
            id="For every disk in the section a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If the section is empty, no Services are discovered.",
        ),
    ],
)
def test_aws_ebs_discovery(
    string_table: StringTable,
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ebs_burst_balance")]
    parse_function = fix_register.agent_sections[SectionName("aws_ebs")].parse_function

    assert list(check.discovery_function(parse_function(string_table))) == discovery_result


@pytest.mark.parametrize(
    "item, params, string_table, expected_check_result",
    [
        pytest.param(
            "123",
            {},
            STRING_TABLE,
            [
                Result(state=State.OK, summary="Balance: <0.01%"),
                Metric("aws_burst_balance", 0.0030055),
            ],
            id="If the item is present, the check result is the appropriate values from the check_levels function.",
        ),
        pytest.param(
            "122",
            {},
            STRING_TABLE,
            [],
            id="If the item is not present, no result is returned.",
        ),
    ],
)
def test_check_aws_ebs_burst_balance(
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_ebs_burst_balance")]
    parse_function = fix_register.agent_sections[SectionName("aws_ebs")].parse_function

    check_result = list(
        check.check_function(
            item=item,
            params=params,
            section=parse_function(string_table),
        )
    )

    assert check_result == expected_check_result
