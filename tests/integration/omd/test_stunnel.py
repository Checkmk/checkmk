#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import subprocess

from tests.testlib.site import Site


def test_stunnel(site: Site) -> None:
    p = site.execute(["stunnel", "-help"], stderr=subprocess.PIPE)
    help_text = p.stderr.read() if p.stderr else ""
    # TODO: Sync this with a global version for stunnel (like we do it for python)
    assert "stunnel 5.63" in help_text
