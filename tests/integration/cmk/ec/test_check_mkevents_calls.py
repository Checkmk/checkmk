#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import pytest  # type: ignore[import]


@pytest.mark.parametrize("args", [
    [],
    ["-a"],
])
def test_simple_check_mkevents_call(site, args):
    p = site.execute(["./check_mkevents"] + args + ["somehost"],
                     stdout=subprocess.PIPE,
                     cwd=site.path("lib/nagios/plugins"))
    output = p.stdout.read()
    assert output == "OK - no events for somehost\n"
    assert p.wait() == 0
