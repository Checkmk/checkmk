#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.broadcom_storage.agent_based.lsi_3ware_disks import (
    check_3ware_disks,
)
from cmk.plugins.broadcom_storage.agent_based.lsi_3ware_disks import (
    discover_3ware_disks as discover_3ware_disks,
)


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
            ["p0", "p1", "p2", "p3"],
        ),
    ],
)
def test_discover_3ware_disks(info: StringTable, expected_discoveries: list[str]) -> None:
    """Test discovery function for 3ware_disks check."""
    services = list(discover_3ware_disks(info))
    result = [service.item for service in services if service.item is not None]
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_state, expected_summary",
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
            State.OK,
            "disk status is OK (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
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
            State.OK,
            "disk status is VERIFYING (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
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
            State.WARN,
            "disk status is SMART_FAILURE (unit: u0, size: 465.76,GB, type: SATA, model: ST3500320SV)",
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
            State.CRIT,
            "disk status is FOOBAR (unit: u0, size: 465.76,GB, type: SATA, model: ST3500418AS)",
        ),
    ],
)
def test_check_3ware_disks(
    item: str,
    params: Mapping[str, Any],
    info: StringTable,
    expected_state: State,
    expected_summary: str,
) -> None:
    """Test check function for 3ware_disks check."""
    results = list(check_3ware_disks(item, params, info))
    assert len(results) == 1
    assert isinstance(results[0], Result)
    assert results[0].state == expected_state
    assert results[0].summary == expected_summary
