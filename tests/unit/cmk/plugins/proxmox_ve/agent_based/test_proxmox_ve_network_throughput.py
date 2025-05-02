#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_network_throughput as pvnt
from cmk.agent_based.v2 import CheckResult, IgnoreResults, Metric, Result, State

VM_DATA_START = pvnt.parse_proxmox_ve_network_throughput(
    [
        [
            json.dumps(
                {
                    "net_in": "123456",
                    "net_out": "123456",
                    "uptime": "0",
                }
            )
        ]
    ]
)

VM_DATA_END = pvnt.parse_proxmox_ve_network_throughput(
    [
        [
            json.dumps(
                {
                    "net_in": "234567",
                    "net_out": "234567",
                    "uptime": "10",
                }
            )
        ]
    ]
)


@pytest.mark.parametrize(
    "params,section_start,section_end,expected_results",
    [
        (
            {"in_levels": ("no_levels", None), "out_levels": ("no_levels", None)},
            VM_DATA_START,
            VM_DATA_END,
            (
                Result(state=State.OK, summary="Inbound: 11.1 kB/s"),
                Metric(name="net_in_throughput", value=11111.1),
                Result(state=State.OK, summary="Outbound: 11.1 kB/s"),
                Metric(name="net_out_throughput", value=11111.1),
            ),
        ),
        (
            {"in_levels": ("fixed", (10000, 10000)), "out_levels": ("fixed", (10000, 10000))},
            VM_DATA_START,
            VM_DATA_END,
            (
                Result(
                    state=State.CRIT,
                    summary="Inbound: 11.1 kB/s (warn/crit at 10.0 kB/s/10.0 kB/s)",
                ),
                Metric(name="net_in_throughput", value=11111.1, levels=(10000.0, 10000.0)),
                Result(
                    state=State.CRIT,
                    summary="Outbound: 11.1 kB/s (warn/crit at 10.0 kB/s/10.0 kB/s)",
                ),
                Metric(name="net_out_throughput", value=11111.1, levels=(10000.0, 10000.0)),
            ),
        ),
    ],
)
@pytest.mark.usefixtures("initialised_item_state")
def test_check_proxmox_ve_vm_info(
    params: Mapping[str, object],
    section_start: pvnt.Section,
    section_end: pvnt.Section,
    expected_results: CheckResult,
) -> None:
    assert tuple(pvnt.check_proxmox_ve_network_throughput(params, section_start)) == (
        IgnoreResults(
            "Counter 'net_in' has been initialized. Result available on second check execution."
        ),
        IgnoreResults(
            "Counter 'net_out' has been initialized. Result available on second check execution."
        ),
    )
    assert tuple(pvnt.check_proxmox_ve_network_throughput(params, section_end)) == expected_results
