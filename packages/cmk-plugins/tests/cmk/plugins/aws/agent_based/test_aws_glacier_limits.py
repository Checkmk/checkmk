#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.aws.agent_based.aws_glacier_limits import (
    check_aws_glacier_limits,
    discover_aws_glacier_limits,
)
from cmk.plugins.aws.lib import parse_aws_limits_generic


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ap-northeast-2"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ca-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "2,", '"eu-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"us-east-1"]]'],
            ],
            [
                Service(item="ap-northeast-2"),
                Service(item="ca-central-1"),
                Service(item="eu-central-1"),
                Service(item="us-east-1"),
            ],
        ),
    ],
)
def test_discover_aws_glacier_limits(
    info: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for aws_glacier_limits check."""
    parsed = parse_aws_limits_generic(info)
    assert list(discover_aws_glacier_limits(parsed)) == list(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "ap-northeast-2",
            {"number_of_vaults": (None, 80.0, 90.0)},
            [
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ap-northeast-2"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ca-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "2,", '"eu-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"us-east-1"]]'],
            ],
            [
                Metric("aws_glacier_number_of_vaults", 0.0),
                Result(state=State.OK, notice="Vaults: 0 (of max. 1000), 0%"),
            ],
        ),
        (
            "eu-central-1",
            {"number_of_vaults": (None, 80.0, 90.0)},
            [
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ap-northeast-2"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ca-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "2,", '"eu-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"us-east-1"]]'],
            ],
            [
                Metric("aws_glacier_number_of_vaults", 2.0),
                Result(state=State.OK, notice="Vaults: 2 (of max. 1000), 0.20%"),
            ],
        ),
    ],
)
def test_check_aws_glacier_limits(
    item: str,
    params: Mapping[str, Any],
    info: StringTable,
    expected_results: Sequence[Metric | Result],
) -> None:
    """Test check function for aws_glacier_limits check."""
    parsed = parse_aws_limits_generic(info)
    assert list(check_aws_glacier_limits(item, params, parsed)) == list(expected_results)
