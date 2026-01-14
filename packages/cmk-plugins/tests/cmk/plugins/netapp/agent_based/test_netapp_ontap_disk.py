#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from typing import Any

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, Metric, Result, State, TableRow
from cmk.plugins.netapp.agent_based.netapp_ontap_disk import (
    check_netapp_ontap_disk_summary,
    inventorize_netapp_ontap_disk,
)
from cmk.plugins.netapp.models import DiskModel


class DiskModelFactory(ModelFactory):
    __model__ = DiskModel


def test_inventorize_netapp_ontap_disk() -> None:
    disk_models = [
        # inventory function will sort the disks by uid
        DiskModelFactory.build(uid="sort_c", serial_number="serial1", vendor="vendor1", bay=1),
        DiskModelFactory.build(uid="sort_a", serial_number="serial2", vendor="vendor2", bay=2),
        DiskModelFactory.build(uid="sort_z", serial_number="serial3", vendor="vendor3", bay=None),
    ]

    result = inventorize_netapp_ontap_disk(section=disk_models)
    assert list(result) == [
        TableRow(
            path=["hardware", "storage", "disks"],
            key_columns={"signature": "sort_a"},
            inventory_columns={"serial": "serial2", "vendor": "vendor2", "bay": 2},
            status_columns={},
        ),
        TableRow(
            path=["hardware", "storage", "disks"],
            key_columns={"signature": "sort_c"},
            inventory_columns={"serial": "serial1", "vendor": "vendor1", "bay": 1},
            status_columns={},
        ),
        TableRow(
            path=["hardware", "storage", "disks"],
            key_columns={"signature": "sort_z"},
            inventory_columns={"serial": "serial3", "vendor": "vendor3", "bay": None},
            status_columns={},
        ),
    ]


_DISK_MODELS = [
    DiskModelFactory.build(
        container_type="normal",
        bytes_per_sector=10,
        sector_count=5,
    ),
    DiskModelFactory.build(
        container_type="normal",
        bytes_per_sector=10,
        sector_count=5,
    ),
    DiskModelFactory.build(
        container_type="normal",
        bytes_per_sector=10,
        sector_count=5,
        serial_number="normal",
    ),
    DiskModelFactory.build(
        container_type="spare",
        bytes_per_sector=10,
        sector_count=5,
    ),
    DiskModelFactory.build(
        container_type="remote",
        bytes_per_sector=10,
        sector_count=5,
    ),
]


@pytest.mark.parametrize(
    "params, expected_results",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Spare disks: 1"),
                Metric("spare_disks", 1.0),
                Result(state=State.OK, summary="Failed disks: 0"),
                Metric("failed_disks", 0.0),
            ],
            id="disks summary ok",
        ),
        pytest.param(
            {
                "number_of_spare_disks": (2.0, 1.0),
            },
            [
                Result(
                    state=State.WARN,
                    summary="Spare disks: 1 (warn/crit below 2/1)",
                ),
                Metric("spare_disks", 1.0),
                Result(state=State.OK, summary="Failed disks: 0"),
                Metric("failed_disks", 0.0),
            ],
            id="disks summary with spare",
        ),
    ],
)
def test_check_netapp_ontap_disk_summary(
    params: Mapping[str, Any], expected_results: CheckResult
) -> None:
    result = list(check_netapp_ontap_disk_summary(params=params, section=_DISK_MODELS))

    assert result[:4] == [
        Result(state=State.OK, summary="Total raw capacity: 200 B"),
        Metric("disk_capacity", 200.0),
        Result(state=State.OK, summary="Total disks: 4"),
        Metric("disks", 4.0),
    ]

    assert result[4:] == expected_results


def test_check_netapp_ontap_disk_summary_failed() -> None:
    params = {
        "failed_spare_ratio": (1.0, 50.0),
        "offline_spare_ratio": (1.0, 50.0),
    }

    disk_models = [
        DiskModelFactory.build(
            container_type="broken",
            bytes_per_sector=10,
            sector_count=5,
            serial_number="failed_disk",
        ),
    ]

    result = list(check_netapp_ontap_disk_summary(params=params, section=disk_models))

    assert result[4] == Result(state=State.OK, summary="Spare disks: 0")
    assert result[5] == Metric("spare_disks", 0.0)
    assert result[6] == Result(state=State.OK, summary="Failed disks: 1")
    assert isinstance(result[7], Metric)
    assert result[7].name == "failed_disks"
    assert result[8] == Result(
        state=State.OK, summary="failed Disk Details: Serial: failed_disk, Size: 50 B"
    )
    assert isinstance(result[9], Result)
    assert result[9].state == State.CRIT
    assert result[9].summary.startswith("Too many failed disks")
