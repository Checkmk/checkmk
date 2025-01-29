#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.collection.agent_based.cadvisor_diskstat import (
    check_cadvisor_diskstat,
    discover_cadvisor_diskstat,
    Section,
)

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
    section: Section,
    discovered_services: Sequence[Service],
) -> None:
    assert list(discover_cadvisor_diskstat(section)) == discovered_services


@pytest.mark.usefixtures("initialised_item_state")
def test_check_cadvisor_diskstat() -> None:
    check_result = list(check_cadvisor_diskstat(item="Summary", params={}, section=SECTION))
    assert len(check_result) == 10  # A Result and Metric for every field in the section


def test_check_cadvisor_diskstat_item_not_found() -> None:
    check_result = list(check_cadvisor_diskstat(item="not_found", params={}, section=SECTION))
    assert not check_result
