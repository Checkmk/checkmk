#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import subprocess

from tests.testlib.site import Site


def test_plugin_validation(plugin_validation_site: Site) -> None:
    p = plugin_validation_site.execute(
        ["cmk-validate-plugins"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, _ = p.communicate()
    assert p.returncode == 0, stdout
