#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Service, StringTable
from cmk.plugins.collection.agent_based import hr_ps


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
def test_hr_ps_discovery(
    info: StringTable,
    discovery_params: Mapping[str, object],
    expected_discovery_result: Sequence[tuple[str, Mapping[str, object]]],
) -> None:
    """Test that the hr_ps check returns the correct discovery results given different
    discovery parameters.
    """
    assert sorted(hr_ps.discover_hr_ps([discovery_params, {}], hr_ps.parse_hr_ps(info))) == sorted(
        Service(item=i, parameters=p) for i, p in expected_discovery_result
    )
