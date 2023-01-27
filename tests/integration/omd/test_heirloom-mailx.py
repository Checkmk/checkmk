#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import subprocess

from tests.testlib.site import Site


def test_heirloommailx(site: Site) -> None:
    p = site.execute(["heirloom-mailx", "-V"], stdout=subprocess.PIPE)
    help_text = p.stdout.read() if p.stdout else "<NO STDOUT>"
    # TODO: Sync this with a global version for heirloom (like we do it for python)
    assert "12.5" in help_text
