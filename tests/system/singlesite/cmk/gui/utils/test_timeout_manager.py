#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from tests.testlib.site import PythonHelper, Site


@pytest.mark.parametrize("test_name", ["raises_timeout", "disable"])
def test_timeout_manager_raises_timeout(site: Site, test_name: str) -> None:
    """Executes TimeoutManager tests in the site context.

    See timeout_manager_test.py for the actual test cases.
    """
    PythonHelper(site, Path(__file__).parent / "timeout_manager_test.py").check_output(
        args=[test_name]
    )
