#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.gui.monitor.command import fake_check_output


def test_without_output_says_who_set_which_state() -> None:
    assert (
        fake_check_output(output=" ", metrics="", state_title="Down", author=UserId("harry"))
        == "Manually set to Down by harry"
    )


def test_keeps_the_given_output() -> None:
    assert (
        fake_check_output(output="Testing", metrics="", state_title="Down", author=UserId("harry"))
        == "Testing"
    )


def test_appends_the_metrics_as_performance_data() -> None:
    assert (
        fake_check_output(
            output="Testing", metrics=" load1=5;10;20 ", state_title="OK", author=UserId("harry")
        )
        == "Testing|load1=5;10;20"
    )
