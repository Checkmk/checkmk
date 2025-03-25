#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.site import Site


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["-a"],
    ],
)
def test_simple_check_mkevents_call(site: Site, args: list[str]) -> None:
    stdout = site.check_output(
        [site.path("lib/nagios/plugins/check_mkevents").as_posix()] + args + ["somehost"],
    )
    assert stdout == "OK - no events for somehost\n"
