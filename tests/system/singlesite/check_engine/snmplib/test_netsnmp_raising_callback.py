#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.testlib.system.site import Site


@pytest.mark.usefixtures("snmpsim")
def test_exception_in_any_netsnmp_callback_is_raised_by_the_request(site: Site) -> None:
    report = json.loads(
        site.python_helper("helper_netsnmp_raising_callback.py").check_output(
            args=["127.0.0.1:1337"]
        )
    )

    assert set(report) == {"get", "getnext", "getbulk", "walk", "set"}
    for operation, result in report.items():
        assert result["callbacks"] > 0, operation
        assert result["unexpected"] == {}, operation
