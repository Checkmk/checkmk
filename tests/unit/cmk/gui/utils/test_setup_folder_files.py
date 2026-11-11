#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils.setup_folder_files import folder_path_from_filename


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("/wato/hosts.mk", ""),
        ("/wato/network/hosts.mk", "network"),
        ("/wato/network/switches/hosts.mk", "network/switches"),
        ("/omd/sites/heute/etc/nagios/conf.d/hosts.mk", None),
        ("/wato/network/switches/other.mk", None),
        ("/watoo/network/hosts.mk", None),
        ("/wato/network/other_hosts.mk", None),
    ],
)
def test_folder_path_from_filename(filename: str, expected: str | None) -> None:
    assert folder_path_from_filename(filename) == expected
