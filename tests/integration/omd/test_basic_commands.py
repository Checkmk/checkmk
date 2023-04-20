#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_basic_commands(site: Site) -> None:
    commands = [
        "bin/mkp",
        "bin/check_mk",
        "bin/cmk",
        "bin/omd",
        "bin/stunnel",
        "bin/cmk-update-config",
    ]

    if not site.version.is_raw_edition():
        commands.append("bin/fetcher")

    for rel_path in commands:
        assert site.file_exists(rel_path)
