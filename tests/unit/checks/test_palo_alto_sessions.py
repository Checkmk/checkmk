#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from .checktestlib import Check

pytestmark = pytest.mark.checks


def test_total_sessions_perfdata_carries_levels_scaled_to_supported_sessions() -> None:
    info = [["262142", "6785", "4432", "2337", "13", "0"]]

    _state, _infotext, perfdata = Check("palo_alto_sessions").run_check(
        None, {"levels_sessions_used": (60, 70)}, info
    )

    assert perfdata[0] == ("total_active_sessions", 6785, 157285.2, 183499.4, 0, 262142)


def test_total_sessions_perfdata_has_no_levels_without_supported_sessions() -> None:
    info = [["0", "5", "3", "2", "0", "0"]]

    _state, _infotext, perfdata = Check("palo_alto_sessions").run_check(
        None, {"levels_sessions_used": (60, 70)}, info
    )

    assert perfdata[0] == ("total_active_sessions", 5)
