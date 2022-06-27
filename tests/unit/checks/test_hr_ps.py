#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import assertDiscoveryResultsEqual, DiscoveryResult, MockHostExtraConf

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, discovery_params, expected_discovery_result",
    [
        (
            [
                ["systemd", "/usr/lib/systemd/systemd", "2"],
                ["lvmetad", "/usr/sbin/lvmetad", "2"],
                ["tuned", "/usr/bin/python2", "2"],
                ["sshd", "/usr/sbin/sshd", "2"],
                ["java", "/usr/lib/jvm/jre-11-openjdk/bin/java", "2"],
                ["sssd", "/usr/sbin/sssd", "2"],
                ["snmpd", "/usr/sbin/snmpd", "1"],
            ],
            {
                "descr": "sshd",
                "match_name_or_path": ("match_name", "sshd"),
            },
            [
                (
                    "sshd",
                    {
                        "match_name_or_path": ("match_name", "sshd"),
                        "match_status": None,
                        "match_groups": [],
                    },
                ),
            ],
        ),
        (
            [
                ["systemd", "/usr/lib/systemd/systemd", "2"],
                ["lvmetad", "/usr/sbin/lvmetad", "2"],
                ["tuned", "/usr/bin/python2", "2"],
                ["sshd", "/usr/sbin/sshd", "2"],
                ["java", "/usr/lib/jvm/jre-11-openjdk/bin/java", "2"],
                ["sssd", "/usr/sbin/sssd", "2"],
                ["snmpd", "/usr/sbin/snmpd", "1"],
            ],
            {
                "descr": "sshd",
                "match_name_or_path": ("match_path", "/usr/sbin/sshd"),
            },
            [
                (
                    "sshd",
                    {
                        "match_name_or_path": ("match_path", "/usr/sbin/sshd"),
                        "match_status": None,
                        "match_groups": [],
                    },
                ),
            ],
        ),
        (
            [
                ["systemd", "/usr/lib/systemd/systemd", "2"],
                ["lvmetad", "/usr/sbin/lvmetad", "2"],
                ["tuned", "/usr/bin/python2", "2"],
                ["sshd", "/usr/sbin/sshd", "2"],
                ["java", "/usr/lib/jvm/jre-11-openjdk/bin/java", "2"],
                ["sssd", "/usr/sbin/sssd", "2"],
                ["snmpd", "/usr/sbin/snmpd", "1"],
            ],
            {
                "descr": "sshd",
                "match_name_or_path": ("match_path", "~.*/sshd$"),
            },
            [
                (
                    "sshd",
                    {
                        "match_name_or_path": ("match_path", "~.*/sshd$"),
                        "match_status": None,
                        "match_groups": [],
                    },
                ),
            ],
        ),
    ],
)
def test_hr_ps_discovery(info, discovery_params, expected_discovery_result) -> None:
    """Test that the hr_ps check returns the correct discovery results given different
    discovery parameters.
    """
    check = Check("hr_ps")

    with MockHostExtraConf(check, discovery_params, "host_extra_conf"):
        actual_discovery_result = check.run_discovery(check.run_parse(info))

    assertDiscoveryResultsEqual(
        check,
        DiscoveryResult(actual_discovery_result),
        DiscoveryResult(expected_discovery_result),
    )
