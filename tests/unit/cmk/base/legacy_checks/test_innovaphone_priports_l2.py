#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.innovaphone_priports_l2 import check_innovaphone_priports_l2


def test_check_innovaphone_priports_l2_unknown_state_is_unknown() -> None:
    info = [["Port 1", "0", "1"]]

    assert check_innovaphone_priports_l2("Port 1", {"mode": 1}, info) == (
        3,
        "State: unknown (0), Mode: TE",
    )


def test_check_innovaphone_priports_l2_unknown_mode_in_discovered_mode_is_ok() -> None:
    info = [["Port 1", "2", "0"]]

    assert check_innovaphone_priports_l2("Port 1", {"mode": 0}, info) == (
        0,
        "State: UP, Mode: unknown (0)",
    )
