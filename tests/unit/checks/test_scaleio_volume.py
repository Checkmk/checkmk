#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import NamedTuple

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


class ScaleioVolume(NamedTuple):
    volume_id: str
    name: str
    size: float
    size_unit: str
    read_ios: Sequence[str]
    write_ios: Sequence[str]


SECTION = {
    "c07a5f6c00000001": ScaleioVolume(
        "c07a5f6c00000001",
        "CF1SIOVCD001",
        2.0,
        "TB",
        ["4", "IOPS", "7.0", "KB", "(7168", "Bytes)", "per-second"],
        ["10", "IOPS", "31.0", "KB", "(31744", "Bytes)", "per-second"],
    ),
    "c07a867c00000002": ScaleioVolume(
        "c07a867c00000002",
        "CF1SIOVCD002",
        5.0,
        "TB",
        ["7", "IOPS", "43.0", "KB", "(44032", "Bytes)", "per-second"],
        ["28", "IOPS", "106.0", "KB", "(108544", "Bytes)", "per-second"],
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
    parsed_section: Mapping[str, Mapping[str, Sequence[str]]],
    discovered_services: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("scaleio_volume")]
    assert list(check.discovery_function(parsed_section)) == discovered_services


def test_check_scaleio_volume(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("scaleio_volume")]
    check_result = list(check.check_function(item=ITEM, params={}, section=SECTION))
    assert check_result[0] == Result(state=State.OK, summary="Name: CF1SIOVCD001, Size: 2.0 TB")
    assert len(check_result) == 9
