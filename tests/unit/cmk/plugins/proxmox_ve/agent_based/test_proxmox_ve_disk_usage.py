#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_disk_usage as pvdu
from cmk.agent_based.v2 import CheckResult, Metric, Result, State

DISK_DATA = {"disk": 1024**4, "max_disk": 2 * 1024**4}


@pytest.mark.parametrize(
    "params,section,expected_results",
    (
        (
            {"levels": ("no_levels", None)},
            DISK_DATA,
            (
                Metric(
                    "fs_used",
                    1099511627776.0,
                    boundaries=(0.0, 2199023255552.0),
                ),
                Metric(
                    "fs_free",
                    1099511627776.0,
                    boundaries=(0.0, None),
                ),
                Result(
                    state=State.OK,
                    summary="Used: 50.00%",
                ),
                Metric(
                    "fs_used_percent",
                    50.0,
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.OK,
                    summary="1.10 TB of 2.20 TB",
                ),
                Metric(
                    "fs_size",
                    2199023255552.0,
                    boundaries=(0.0, None),
                ),
            ),
        ),
        (
            {"levels": ("fixed", (40.0, 90.0))},
            DISK_DATA,
            (
                Metric(
                    "fs_used",
                    1099511627776.0,
                    levels=(879609302220.8, 1979120929996.8),
                    boundaries=(0.0, 2199023255552.0),
                ),
                Metric(
                    "fs_free",
                    1099511627776.0,
                    boundaries=(0.0, None),
                ),
                Result(state=State.WARN, summary="Used: 50.00% (warn/crit at 40.00%/90.00%)"),
                Metric(
                    "fs_used_percent",
                    50.0,
                    levels=(40.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="1.10 TB of 2.20 TB"),
                Metric(
                    "fs_size",
                    2199023255552.0,
                    boundaries=(0.0, None),
                ),
            ),
        ),
    ),
)
def test_check_proxmox_ve_disk_usage(
    params: Mapping[str, object], section: pvdu.Section, expected_results: CheckResult
) -> None:
    results = tuple(pvdu.check_proxmox_ve_disk_usage(params, section))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    assert not pytest.main(["--doctest-modules", pvdu.__file__])
    pytest.main(["-vvsx", __file__])
