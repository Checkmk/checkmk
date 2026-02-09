#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib.site import PythonHelper, Site


def test_icon_modes(site: Site) -> None:
    PythonHelper(site, Path(__file__).parent / "icon_test.py").check_output(args=["main"])
