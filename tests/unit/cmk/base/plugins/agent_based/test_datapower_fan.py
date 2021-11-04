#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.datapower_fan import Fan, parse_datapower_fan


def test_parse_datapower_fan() -> None:
    assert parse_datapower_fan(
        [
            ["11", "9700", "4"],
            ["12", "5600", "5"],
            ["13", "9800", "7"],
            ["14", "5400", "10"],
        ]
    ) == {
        "Tray 1 Fan 1": Fan(
            state="4",
            state_txt="operating normally",
            speed="9700",
        ),
        "Tray 1 Fan 2": Fan(
            state="5",
            state_txt="reached upper non-critical limit",
            speed="5600",
        ),
        "Tray 1 Fan 3": Fan(
            state="7",
            state_txt="reached upper non-recoverable limit",
            speed="9800",
        ),
        "Tray 1 Fan 4": Fan(
            state="10",
            state_txt="Invalid",
            speed="5400",
        ),
    }
