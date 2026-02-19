#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

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
        "bin/cmk-config-anonymizer",
        "bin/cmk-validate-plugins",
    ]

    if not site.edition.is_community_edition():
        commands.append("bin/fetcher")

    for rel_path in commands:
        assert site.file_exists(rel_path)


@pytest.mark.parametrize(
    "command",
    [
        ["bc", "--help"],
        ["curl", "--help"],
        ["dig", "-v"],
        ["file", "--help"],
        ["host", "-V"],
        ["nc", "-h"],
        # ["nmap", "--help"], # not present in build images
        ["nslookup", "help"],
        ["pdftoppm", "--help"],
        ["php", "--help"],
        ["php-cgi", "--help"],
        ["resolvectl", "--help"],
        ["rpmbuild", "--help"],
        ["which", "scp"],
        ["ssh", "-V"],
        ["systemctl", "--help"],
        ["zypper", "--help"],
    ],
    ids=lambda cmd: cmd[0],
)
def test_additional_os_command_availability(site: Site, command: list[str]) -> None:
    # 'zypper' is only available in SLES-based images, so we skip the test if it's not present.
    if command[0] == "zypper" and not os.environ.get("DISTRO", "").startswith("sles"):
        pytest.skip("'zypper' is not available in this image")

    # Commands executed here should return with exit code 0
    site.check_output(command)
