#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.site import Site


def test_basic_commands(site: Site) -> None:
    commands = [
        "bin/mkp",
        "bin/check_mk",
        "bin/cmk",
        "bin/omd",
        "bin/stunnel",
        "bin/cmk-broker-test",
        "bin/cmk-piggyback",
        "bin/cmk-piggyback-hub",
        "bin/cmk-update-config",
        "bin/cmk-validate-plugins",
    ]

    if not site.edition.is_raw_edition():
        commands.append("bin/fetcher")

    for rel_path in commands:
        assert site.file_exists(rel_path)


@pytest.mark.parametrize(
    "command",
    [
        ["bc", "--help"],
        ["file", "--help"],
    ],
)
def test_additional_os_command_availability(site: Site, command: list[str]) -> None:
    # Commands executed here should return with exit code 0
    site.check_output(command)
