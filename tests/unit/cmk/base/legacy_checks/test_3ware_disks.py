#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

import importlib
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable

threware_disks = importlib.import_module("cmk.base.legacy_checks.3ware_disks")
check_3ware_disks = threware_disks.check_3ware_disks
discover_3ware_disks = threware_disks.inventory_3ware_disks


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                ["p0", "OK", "u0", "465.76", "GB", "SATA", "0", "-", "ST3500418AS"],
                ["p1", "VERIFYING", "u0", "465.76", "GB", "SATA", "1", "-", "ST3500418AS"],
                ["p2", "SMART_FAILURE", "u0", "465.76", "GB", "SATA", "2", "-", "ST3500320SV"],
                ["p3", "FOOBAR", "u0", "465.76", "GB", "SATA", "3", "-", "ST3500418AS"],
            ],
            [("p0", {}), ("p1", {}), ("p2", {}), ("p3", {})],
        ),
    ],
)
def test_discover_3ware_disks(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for 3ware_disks check."""
    result = list(discover_3ware_disks(info))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "p0",
            {},
            [
                ["p0", "OK", "u0", "465.76", "GB", "SATA", "0", "-", "ST3500418AS"],
                ["p1", "VERIFYING", "u0", "465.76", "GB", "SATA", "1", "-", "ST3500418AS"],
                ["p2", "SMART_FAILURE", "u0", "465.76", "GB", "SATA", "2", "-", "ST3500320SV"],
                ["p3", "FOOBAR", "u0", "465.76", "GB", "SATA", "3", "-", "ST3500418AS"],
            ],
            [
                0,
                "disk status is OK (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
            ],
        ),
        (
            "p1",
            {},
            [
                ["p0", "OK", "u0", "465.76", "GB", "SATA", "0", "-", "ST3500418AS"],
                ["p1", "VERIFYING", "u0", "465.76", "GB", "SATA", "1", "-", "ST3500418AS"],
                ["p2", "SMART_FAILURE", "u0", "465.76", "GB", "SATA", "2", "-", "ST3500320SV"],
                ["p3", "FOOBAR", "u0", "465.76", "GB", "SATA", "3", "-", "ST3500418AS"],
            ],
            [
                0,
                "disk status is VERIFYING (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
            ],
        ),
        (
            "p2",
            {},
            [
                ["p0", "OK", "u0", "465.76", "GB", "SATA", "0", "-", "ST3500418AS"],
                ["p1", "VERIFYING", "u0", "465.76", "GB", "SATA", "1", "-", "ST3500418AS"],
                ["p2", "SMART_FAILURE", "u0", "465.76", "GB", "SATA", "2", "-", "ST3500320SV"],
                ["p3", "FOOBAR", "u0", "465.76", "GB", "SATA", "3", "-", "ST3500418AS"],
            ],
            [
                1,
                "disk status is SMART_FAILURE (unit: u0, size: 465.76,GB, type: SATA, model: ST3500320SV)",
            ],
        ),
        (
            "p3",
            {},
            [
                ["p0", "OK", "u0", "465.76", "GB", "SATA", "0", "-", "ST3500418AS"],
                ["p1", "VERIFYING", "u0", "465.76", "GB", "SATA", "1", "-", "ST3500418AS"],
                ["p2", "SMART_FAILURE", "u0", "465.76", "GB", "SATA", "2", "-", "ST3500320SV"],
                ["p3", "FOOBAR", "u0", "465.76", "GB", "SATA", "3", "-", "ST3500418AS"],
            ],
            [
                2,
                "disk status is FOOBAR (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
            ],
        ),
    ],
)
def test_check_3ware_disks(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for 3ware_disks check."""
    result = list(check_3ware_disks(item, params, info))
    assert result == expected_results
