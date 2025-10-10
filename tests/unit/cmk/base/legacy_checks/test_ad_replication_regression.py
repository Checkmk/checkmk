#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import time_machine

from cmk.base.legacy_checks.ad_replication import (
    check_ad_replication,
    inventory_ad_replication,
    parse_ad_replication,
)

# Test data from generictests/datasets/ad_replication_regression.py
test_info = [
    [
        "showrepl_COLUMNS,Destination",
        "DSA",
        "Site,Destination",
        "DSA,Naming",
        "Context,Source",
        "DSA",
        "Site,Source",
        "DSA,Transport",
        "Type,Number",
        "of",
        "Failures,Last",
        "Failure",
        "Time,Last",
        "Success",
        "Time,Last",
        "Failure",
        "Status",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        "09:15:37,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        "09:18:37,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        "09:18:37,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        "09:18:38,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        "08:48:03,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        "09:18:52,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        "09:18:55,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        "09:19:00,0",
    ],
    [
        'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        "09:19:01,0",
    ],
    ["showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS003,RPC,0,0,2015-07-07", "08:48:03,0"],
    ["showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS055,RPC,0,0,2015-07-07", "08:48:03,0"],
    ["showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS008,RPC,0,0,2015-07-07", "08:48:03,0"],
]


@time_machine.travel("2015-07-12 00:00:00")
def test_ad_replication_discovery() -> None:
    """Test discovery function of ad_replication check."""
    section = parse_ad_replication(test_info)
    result = list(inventory_ad_replication(section))

    assert result == [
        ("HAM/SADS055", {}),
        ("HAM/SADS008", {}),
        ("HAM/SADS015", {}),
        ("HAM/SADS003", {}),
    ]


@time_machine.travel("2015-07-12 00:00:00")
def test_ad_replication_check_ok() -> None:
    """Test check function with OK status."""
    section = parse_ad_replication(test_info)
    params: dict[str, Any] = {"failure_levels": (15, 20)}

    result = list(check_ad_replication("HAM/SADS003", params, section))
    assert result == [(0, "All replications are OK.")]


@time_machine.travel("2015-07-12 00:00:00")
def test_ad_replication_check_warn() -> None:
    """Test check function with warning status."""
    section = parse_ad_replication(test_info)
    params: dict[str, Any] = {"failure_levels": (-1, 2)}

    result = list(check_ad_replication("HAM/SADS015", params, section))

    # Should match the expected output from the dataset
    assert len(result) == 2
    assert result[0][0] == 1  # Warning state
    assert "Replications with failures: 3, Total failures: 0" in result[0][1]
    assert result[1][0] == 0  # OK state for detailed output
    assert "reached  the threshold of maximum failures" in result[1][1]
