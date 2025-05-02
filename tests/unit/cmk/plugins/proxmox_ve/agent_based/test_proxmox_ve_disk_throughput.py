#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_disk_throughput as pvdt
from cmk.agent_based.v1 import IgnoreResults
from cmk.agent_based.v2 import CheckResult, Metric, Result, State

VM_DATA_START = pvdt.parse_proxmox_ve_disk_throughput(
    [[json.dumps({"disk_read": "123456", "disk_write": "123456", "uptime": 0})]]
)

VM_DATA_END = pvdt.parse_proxmox_ve_disk_throughput(
    [[json.dumps({"disk_read": "234567", "disk_write": "234567", "uptime": 10})]]
)


@pytest.mark.parametrize(
    "params,section_start,section_end,expected_results",
    [
        (
            {"read_levels": ("no_levels", None), "write_levels": ("no_levels", None)},
            VM_DATA_START,
            VM_DATA_END,
            (
                Result(state=State.OK, summary="Disk read: 11.1 kB/s"),
                Metric(name="disk_read_throughput", value=11111.1),
                Result(state=State.OK, summary="Disk write: 11.1 kB/s"),
                Metric(name="disk_write_throughput", value=11111.1),
            ),
        ),
        (
            {"read_levels": ("fixed", (10000, 10000)), "write_levels": ("fixed", (10000, 10000))},
            VM_DATA_START,
            VM_DATA_END,
            (
                Result(
                    state=State.CRIT,
                    summary="Disk read: 11.1 kB/s (warn/crit at 10.0 kB/s/10.0 kB/s)",
                ),
                Metric(name="disk_read_throughput", value=11111.1, levels=(10000.0, 10000.0)),
                Result(
                    state=State.CRIT,
                    summary="Disk write: 11.1 kB/s (warn/crit at 10.0 kB/s/10.0 kB/s)",
                ),
                Metric(name="disk_write_throughput", value=11111.1, levels=(10000.0, 10000.0)),
            ),
        ),
    ],
)
@pytest.mark.usefixtures("initialised_item_state")
def test_check_proxmox_ve_vm_info(
    params: Mapping[str, object],
    section_start: pvdt.Section,
    section_end: pvdt.Section,
    expected_results: CheckResult,
) -> None:
    assert tuple(pvdt.check_proxmox_ve_disk_throughput(params, section_start)) == (
        IgnoreResults(
            "Counter 'disk_read' has been initialized. Result available on second check execution."
        ),
        IgnoreResults(
            "Counter 'disk_write' has been initialized. Result available on second check execution."
        ),
    )

    assert tuple(pvdt.check_proxmox_ve_disk_throughput(params, section_end)) == expected_results
