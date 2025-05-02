#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_cpu_util as pvcu
from cmk.agent_based.v2 import CheckResult, Metric, Result, State

VM_DATA = pvcu.parse_proxmox_ve_cpu_util(
    [
        [
            json.dumps(
                {
                    "cpu": "0.75",
                    "max_cpu": "6",
                    "uptime": "0",
                }
            )
        ]
    ]
)


@pytest.mark.parametrize(
    "params,section,expected_results",
    [
        (
            {"util": ("no_levels", None), "average": 1},
            VM_DATA,
            (
                Metric("util", 75.0, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Total CPU (1 min average): 75.00%"),
                Metric("util_average", 75.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="CPU cores assigned: 6"),
                Result(state=State.OK, summary="Total CPU Core usage: 4.50"),
                Metric("cpu_core_usage", 4.5, boundaries=(0.0, 6.0)),
            ),
        ),
        (
            {"util": ("fixed", (90.0, 95.0)), "average": 1},
            VM_DATA,
            (
                Metric("util", 75.0, levels=(90.0, 95.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Total CPU (1 min average): 75.00%"),
                Metric("util_average", 75.0, levels=(90.0, 95.0), boundaries=(0.0, None)),
                Result(state=State.OK, summary="CPU cores assigned: 6"),
                Result(state=State.OK, summary="Total CPU Core usage: 4.50"),
                Metric("cpu_core_usage", 4.5, levels=(5.4, 5.7), boundaries=(0.0, 6.0)),
            ),
        ),
    ],
)
@pytest.mark.usefixtures("initialised_item_state")
def test_check_proxmox_ve_vm_info(
    params: Mapping[str, object], section: pvcu.Section, expected_results: CheckResult
) -> None:
    results = tuple(pvcu.check_proxmox_ve_cpu_util(params, section))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    assert not pytest.main(["--doctest-modules", pvcu.__file__])
    pytest.main(["-T=unit", "-vvsx", __file__])
