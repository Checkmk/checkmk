#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.aws import parse_aws_limits_generic
from cmk.base.legacy_checks.aws_glacier_limits import (
    check_aws_glacier_limits,
    discover_aws_glacier_limits,
)


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
            [("ap-northeast-2", {}), ("ca-central-1", {}), ("eu-central-1", {}), ("us-east-1", {})],
        ),
    ],
)
def test_discover_aws_glacier_limits(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for aws_glacier_limits check."""
    parsed = parse_aws_limits_generic(info)
    result = list(discover_aws_glacier_limits(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
                (0, "No levels reached", [("aws_glacier_number_of_vaults", 0)]),
                (0, "\nVaults: 0 (of max. 1000)"),
            ],
        ),
        (
            "ca-central-1",
            {"number_of_vaults": (None, 80.0, 90.0)},
            [
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ap-northeast-2"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ca-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "2,", '"eu-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"us-east-1"]]'],
            ],
            [
                (0, "No levels reached", [("aws_glacier_number_of_vaults", 0)]),
                (0, "\nVaults: 0 (of max. 1000)"),
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
                (0, "No levels reached", [("aws_glacier_number_of_vaults", 2)]),
                (0, "\nVaults: 2 (of max. 1000)"),
            ],
        ),
        (
            "us-east-1",
            {"number_of_vaults": (None, 80.0, 90.0)},
            [
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ap-northeast-2"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"ca-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "2,", '"eu-central-1"]]'],
                ['[["number_of_vaults",', '"Vaults",', "1000,", "0,", '"us-east-1"]]'],
            ],
            [
                (0, "No levels reached", [("aws_glacier_number_of_vaults", 0)]),
                (0, "\nVaults: 0 (of max. 1000)"),
            ],
        ),
    ],
)
def test_check_aws_glacier_limits(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for aws_glacier_limits check."""
    parsed = parse_aws_limits_generic(info)
    result = list(check_aws_glacier_limits(item, params, parsed))
    assert result == expected_results
