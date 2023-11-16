#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1 import get_value_store, GetRateError, Metric, Result, Service, State
from cmk.agent_based.v1.type_defs import StringTable
from cmk.plugins.aws.agent_based.aws_ebs import (
    check_aws_ebs,
    check_aws_ebs_burst_balance,
    discover_aws_ebs,
    discover_aws_ebs_burst_balance,
    parse_aws_ebs,
)

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
) -> None:
    assert list(discover_aws_ebs(parse_aws_ebs(string_table))) == discovery_result
    assert list(discover_aws_ebs_burst_balance(parse_aws_ebs(string_table))) == discovery_result


@pytest.mark.usefixtures("initialised_item_state")
def test_check_aws_ebs_raise_get_rate_error() -> None:
    with pytest.raises(GetRateError):
        list(
            check_aws_ebs(
                item="123",
                params={},
                section=parse_aws_ebs(STRING_TABLE),
            )
        )


@pytest.mark.usefixtures("initialised_item_state")
def test_check_aws_ebs() -> None:
    get_value_store().update(
        {
            f"{metric}.123": (0, 0)
            for metric in [
                "aws_ebs_disk_io_read_ios",
                "aws_ebs_disk_io_write_ios",
                "aws_ebs_disk_io_read_throughput",
                "aws_ebs_disk_io_write_throughput",
                "aws_ebs_disk_io_queue_len",
            ]
        }
    )
    check_result = check_aws_ebs(
        item="123",
        params={},
        section=parse_aws_ebs(STRING_TABLE),
    )
    assert len(list(check_result)) == 10


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
) -> None:
    check_result = list(
        check_aws_ebs_burst_balance(
            item=item,
            params=params,
            section=parse_aws_ebs(string_table),
        )
    )

    assert check_result == expected_check_result
