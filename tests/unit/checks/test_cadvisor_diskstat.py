#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Service

SECTION = {
    "Summary": {
        "write_ios": 0.0,
        "read_ios": 0.0,
        "utilization": 0.02,
        "read_throughput": 0.0,
        "write_throughput": 0.0,
    }
}


@pytest.mark.parametrize(
    "section, discovered_services",
    [
        pytest.param(
            SECTION,
            [Service(item="Summary")],
            id="A summary service is created for the disks",
        ),
        pytest.param(
            {},
            [],
            id="If no disks is present in the section, no services are discovered",
        ),
    ],
)
def test_discover_cadvisor_diskstat(
    section: Mapping[str, Mapping[str, float]],
    discovered_services: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("cadvisor_diskstat")]
    assert list(check.discovery_function(section)) == discovered_services


def test_check_cadvisor_diskstat(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("cadvisor_diskstat")]
    check_result = list(check.check_function(item="Summary", params={}, section=SECTION))
    assert len(check_result) == 10  # A Result and Metric for every field in the section


def test_check_cadvisor_diskstat_item_not_found(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("cadvisor_diskstat")]
    check_result = list(check.check_function(item="not_found", params={}, section=SECTION))
    assert check_result == []
