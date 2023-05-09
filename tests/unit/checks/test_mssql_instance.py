#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check  # type: ignore[import]


@pytest.fixture
def check_plugin() -> Check:
    return Check("mssql_instance")


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_mssql_instance_vanished(check_plugin: Check) -> None:
    assert list(check_plugin.run_check("MSSQL instance", {}, {})) == [
        (2, "Database or necessary processes not running or login failed"),
    ]
