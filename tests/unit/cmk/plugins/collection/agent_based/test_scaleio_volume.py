#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.scaleio_volume import (
    check_scaleio_volume,
    discover_scaleio_volume,
    ScaleioVolume,
    ScaleioVolumeSection,
)
from cmk.plugins.lib.scaleio import DiskReadWrite, StorageConversionError

SECTION = {
    "c07a5f6c00000001": ScaleioVolume(
        "c07a5f6c00000001",
        "CF1SIOVCD001",
        2.0,
        "TB",
        DiskReadWrite(7168.0, 31744.0, 4.0, 10.0),
    ),
    "c07a867c00000002": ScaleioVolume(
        "c07a867c00000002",
        "CF1SIOVCD002",
        5.0,
        "TB",
        DiskReadWrite(44032.0, 108544.0, 7.0, 28.0),
    ),
}
SECTION_WITH_CONVERSION_ERROR = {
    "c07a5f6c00000001": ScaleioVolume(
        "c07a5f6c00000001",
        "CF1SIOVCD001",
        2.0,
        "TB",
        StorageConversionError(unit="PB"),
    ),
}

ITEM = "c07a5f6c00000001"


@pytest.mark.parametrize(
    "parsed_section, discovered_services",
    [
        pytest.param(
            SECTION,
            [Service(item="c07a5f6c00000001"), Service(item="c07a867c00000002")],
            id="A service is created for each volume that is present in the parsed section",
        ),
        pytest.param(
            {},
            [],
            id="If no volume is present in the parsed section, no services are discovered",
        ),
    ],
)
def test_inventory_scaleio_volume(
    parsed_section: ScaleioVolumeSection,
    discovered_services: Sequence[Service],
) -> None:
    assert list(discover_scaleio_volume(parsed_section)) == discovered_services


@pytest.mark.usefixtures("initialised_item_state")
def test_check_scaleio_volume() -> None:
    check_result = list(check_scaleio_volume(item=ITEM, params={}, section=SECTION))
    assert check_result[0] == Result(state=State.OK, summary="Name: CF1SIOVCD001, Size: 2.0 TB")
    assert len(check_result) == 9


def test_check_scaleio_volume_with_conversion_error() -> None:
    check_result = list(
        check_scaleio_volume(item=ITEM, params={}, section=SECTION_WITH_CONVERSION_ERROR)
    )
    assert check_result[1] == Result(
        state=State.UNKNOWN,
        summary="Unknown unit: PB",
    )
