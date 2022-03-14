#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.proxmox_ve_mem_usage import check_proxmox_ve_mem_usage

MEM_DATA = {"mem": 1024**3, "max_mem": 2 * 1024**3}


@pytest.mark.parametrize(
    "params,section,expected_results",
    [
        (
            {"levels": (40.0, 90.0)},
            MEM_DATA,
            (
                Result(
                    state=State.WARN,
                    summary="Usage: 50.00% - 1.00 GiB of 2.00 GiB (warn/crit at 40.00%/90.00% used)",
                ),
                Metric(
                    "mem_used",
                    1073741824.0,
                    levels=(858993459.2, 1932735283.2),
                    boundaries=(0.0, 2147483648.0),
                ),
                Metric(
                    "mem_used_percent",
                    50.0,
                    levels=(40.0, 90.0),
                    boundaries=(0.0, None),
                ),
            ),
        ),
    ],
)
def test_check_proxmox_ve_mem_usage(params, section, expected_results) -> None:
    results = tuple(check_proxmox_ve_mem_usage(params, section))
    print("\n" + "\n".join(map(str, results)))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    from os.path import dirname, join

    assert not pytest.main(
        [
            "--doctest-modules",
            join(
                dirname(__file__),
                "../../../../../../cmk/base/plugins/agent_based/proxmox_ve_mem_usage.py",
            ),
        ]
    )
    pytest.main(["-T=unit", "-vvsx", __file__])
