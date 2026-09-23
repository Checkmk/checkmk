#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import time_machine

from cmk.base.legacy_checks import innovaphone_priports_l1


@time_machine.travel(60.0)
def test_check_innovaphone_priports_l1_unknown_state(monkeypatch: pytest.MonkeyPatch) -> None:
    # The device reported a port state that is neither Down (1) nor UP (2)
    parsed = innovaphone_priports_l1.parse_innovaphone_priports_l1([["0", "0", "0", "0"]])
    value_store = {"innovaphone_priports_l1.0": (50.0, 0)}
    monkeypatch.setattr(innovaphone_priports_l1, "get_value_store", lambda: value_store)

    assert list(
        innovaphone_priports_l1.check_innovaphone_priports_l1("0", {"err_slip_count": 0}, parsed)
    ) == [(3, "Current state is unknown (0)")]
