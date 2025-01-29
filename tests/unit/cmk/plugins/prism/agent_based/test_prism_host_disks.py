#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_host_disks import (
    check_prism_host_disks,
    discovery_prism_host_disks,
)

SECTION = {
    "disk_hardware_configs": {
        "1": {
            "serial_number": "S456NW0R504267",
            "location": 1,
            "bad": False,
            "mounted": True,
            "model": "SAMSUNG MZ7LH3T8HMLT-00005",
            "vendor": "Not Available",
            "boot_disk": True,
            "only_boot_disk": False,
            "under_diagnosis": False,
            "background_operation": None,
            "current_firmware_version": "A04Q",
        },
        "2": {
            "serial_number": "S456NW0R504278",
            "location": 2,
            "bad": True,
            "mounted": False,
            "model": "SAMSUNG MZ7LH3T8HMLT-00005",
            "vendor": "Not Available",
            "boot_disk": True,
            "only_boot_disk": False,
            "under_diagnosis": False,
            "background_operation": None,
            "current_firmware_version": "A04Q",
        },
        "3": None,
    }
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(item="1"),
                Service(item="2"),
            ],
            id="For every disk, a Service is discovered.",
        ),
        pytest.param(
            {"disk_hardware_configs": {"1": None, "2": None, "3": None}},
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discovery_prism_host_disks(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_host_disks(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["item", "params", "section", "expected_check_result"],
    [
        pytest.param(
            "1",
            {"mounted": True},
            SECTION,
            [
                Result(state=State.OK, summary="Model: SAMSUNG MZ7LH3T8HMLT-00005"),
                Result(state=State.OK, summary="Serial: S456NW0R504267"),
                Result(state=State.OK, summary="State: healthy"),
                Result(state=State.OK, summary="Mount state: disk is mounted"),
            ],
            id="If the disk is in expected mount state and healthy, the check result is OK.",
        ),
        pytest.param(
            "2",
            {"mounted": True},
            SECTION,
            [
                Result(state=State.OK, summary="Model: SAMSUNG MZ7LH3T8HMLT-00005"),
                Result(state=State.OK, summary="Serial: S456NW0R504278"),
                Result(state=State.WARN, summary="State: unhealthy"),
                Result(
                    state=State.WARN,
                    summary="Mount state: disk is not mounted - expected: disk is mounted",
                ),
            ],
            id="If the disk is not in expected mount state and unhealthy, the check result is WARN.",
        ),
    ],
)
def test_check_prism_host_disks(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_host_disks(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
