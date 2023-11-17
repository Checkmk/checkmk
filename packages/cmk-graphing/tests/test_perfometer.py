#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import perfometer


def test_name_error() -> None:
    with pytest.raises(ValueError):
        perfometer.Name("")


def test_perfometer_error_missing_segments() -> None:
    name = perfometer.Name("perfometer-name")
    focus_range = perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100))
    with pytest.raises(AssertionError):
        perfometer.Perfometer(name, focus_range, [])
