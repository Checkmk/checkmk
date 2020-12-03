#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Metric
from cmk.base.plugins.agent_based.proxmox_ve_disk_usage import check_proxmox_ve_disk_usage

DISK_DATA = {"disk": 1024**4, "max_disk": 2 * 1024**4}


@pytest.mark.parametrize(
    "params,section,expected_results",
    (
        (
            {},  # must be explicitly set, evaluates to (0.,0.)
            DISK_DATA,
            (
                Result(
                    state=State.CRIT,
                    summary='Usage: 1.10 TB (warn/crit at 0 B/0 B)',
                ),
                Metric(
                    'fs_used',
                    1099511627776.0,
                    levels=(0.0, 0.0),
                    boundaries=(0.0, 2199023255552.0),
                ),
            ),
        ),
        (
            {
                "levels": (40., 90.)
            },
            DISK_DATA,
            (
                Result(
                    state=State.WARN,
                    summary='Usage: 1.10 TB (warn/crit at 880 GB/1.98 TB)',
                ),
                Metric(
                    'fs_used',
                    1099511627776.0,
                    levels=(879609302220.8, 1979120929996.8),
                    boundaries=(0.0, 2199023255552.0),
                ),
            ),
        ),
    ))
def test_check_proxmox_ve_disk_usage(params, section, expected_results) -> None:
    results = tuple(check_proxmox_ve_disk_usage(params, section))
    print("\n" + "\n".join(map(str, results)))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    from os.path import dirname, join
    assert not pytest.main([
        "--doctest-modules",
        join(dirname(__file__),
             "../../../../../../cmk/base/plugins/agent_based/proxmox_ve_disk_usage.py")
    ])
    pytest.main(["-T=unit", "-vvsx", __file__])
