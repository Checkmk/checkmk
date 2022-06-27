#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, Optional, Sequence, Tuple, TypedDict

import pytest

from tests.testlib import Check

from .checktestlib import assertCheckResultsEqual, CheckResult

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks

agent_out = [
    # Win7 - WM
    """
Name: Windows(R) 7, Enterprise edition
Description: Windows Operating System - Windows(R) 7, TIMEBASED_EVAL channel
Partial Product Key: JCDDG
License Status: Initial grace period
Time remaining: 12960 minute(s) (9 day(s))
""",
    # Win-Server 2012
    """

Name: Windows(R), ServerStandard edition
Description: Windows(R) Operating System, VOLUME_KMSCLIENT channel
Partial Product Key: MDVJX
License Status: Licensed
Volume activation expiration: 253564 minute(s) (177 day(s))
Configured Activation Type: All

Most recent activation information:
Key Management Service client information
Client Machine ID (CMID): f9d4e20a-cb8f-4050-9c0c-56420455ada1
KMS machine name from DNS: bisv229.corp.giag.net:1688
KMS machine IP address: 10.5.213.229
KMS machine extended PID: 06401-00206-491-411285-03-1031-9600.0000-0802017
Activation interval: 120 minutes
Renewal interval: 10080 minutes
KMS host caching is enabled

""",
    # Win-Server 2008
    """

Name: Windows Server(R), ServerStandard edition
Description: Windows Operating System - Windows Server(R), VOLUME_KMSCLIENT chan
nel
Partial Product Key: R7VHC
License Status: Licensed
Volume activation expiration: 251100 minute(s) (174 day(s))

Key Management Service client information
Client Machine ID (CMID): a885c11e-4253-4e4b-825d-24c888769334
KMS machine name from DNS: bisv229.corp.giag.net:1688
KMS machine extended PID: 06401-00206-491-411285-03-1031-9600.0000-0802017
Activation interval: 120 minutes
Renewal interval: 10080 minutes
KMS host caching is enabled""",
    # Win10Pro-VM
    """
Name: Windows(R), Professional edition
Description: Windows(R) Operating System, OEM_DM channel
Partial Product Key: D692P
License Status: Licensed""",
]


def splitter(text):
    return [line.split() for line in text.split("\n")]


@pytest.mark.parametrize(
    "capture, result",
    list(
        zip(
            agent_out,
            [
                {
                    "License": "Initial grace period",
                    "expiration": "12960 minute(s) (9 day(s))",
                    "expiration_time": 12960 * 60,
                },
                {
                    "License": "Licensed",
                    "expiration": "253564 minute(s) (177 day(s))",
                    "expiration_time": 253564 * 60,
                },
                {
                    "License": "Licensed",
                    "expiration": "251100 minute(s) (174 day(s))",
                    "expiration_time": 251100 * 60,
                },
                {
                    "License": "Licensed",
                },
            ],
        )
    ),
    ids=["win7", "win2012", "win2008", "win10"],
)
def test_parse_win_license(capture, result) -> None:
    check = Check("win_license")
    assert result == check.run_parse(splitter(capture))


class CheckParameters(TypedDict):
    status: Sequence[str]
    expiration_time: Tuple[int, int]


class check_ref(NamedTuple):
    parameters: Optional[CheckParameters]
    check_output: CheckResult


@pytest.mark.parametrize(
    "capture, result",
    list(
        zip(
            agent_out,
            [
                check_ref(
                    {
                        "status": ["Licensed", "Initial grace period"],
                        "expiration_time": (8 * 24 * 60 * 60, 5 * 24 * 60 * 60),
                    },
                    CheckResult(
                        [
                            (0, "Software is Initial grace period"),
                            (0, "License will expire in 9 days 0 hours"),
                        ]
                    ),
                ),
                check_ref(
                    {
                        "status": ["Licensed", "Initial grace period"],
                        "expiration_time": (180 * 24 * 60 * 60, 90 * 24 * 60 * 60),
                    },
                    CheckResult(
                        [
                            (0, "Software is Licensed"),
                            (
                                1,
                                "License will expire in 176 days 2 hours (warn/crit at 180 days 0 hours/90 days 0 hours)",
                            ),
                        ]
                    ),
                ),
                check_ref(
                    {
                        "status": ["Licensed", "Initial grace period"],
                        "expiration_time": (360 * 24 * 60 * 60, 180 * 24 * 60 * 60),
                    },
                    CheckResult(
                        [
                            (0, "Software is Licensed"),
                            (
                                2,
                                "License will expire in 174 days 9 hours (warn/crit at 360 days 0 hours/180 days 0 hours)",
                            ),
                        ]
                    ),
                ),
                check_ref(
                    {
                        "status": ["Licensed", "Initial grace period"],
                        "expiration_time": (14 * 24 * 60 * 60, 7 * 24 * 60 * 60),
                    },
                    CheckResult([(0, "Software is Licensed")]),
                ),
            ],
        )
    )
    + list(
        zip(
            agent_out,
            [
                check_ref(
                    {
                        "status": ["Registered"],
                        "expiration_time": (8 * 24 * 60 * 60, 5 * 24 * 60 * 60),
                    },
                    CheckResult(
                        [
                            (2, "Software is Initial grace period Required: Registered"),
                            (0, "License will expire in 9 days 0 hours"),
                        ]
                    ),
                ),
                check_ref(
                    None,
                    CheckResult(
                        [
                            (0, "Software is Licensed"),
                            (0, "License will expire in 176 days 2 hours"),
                        ]
                    ),
                ),
            ],
        )
    ),
    ids=[str(x) for x in range(6)],
)
def test_check_win_license(capture, result) -> None:
    check = Check("win_license")
    output = check.run_check(
        None, result.parameters or check.default_parameters(), check.run_parse(splitter(capture))
    )

    assertCheckResultsEqual(CheckResult(output), result.check_output)
