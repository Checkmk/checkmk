#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Final

from cmk.gui.logged_in import LoggedInUser

GRAPH_PIN_USER_FILE: Final = "graph_pin"


def load_graph_pin(user: LoggedInUser) -> int | None:
    raw_pin_time = user.load_file(GRAPH_PIN_USER_FILE, None)
    return None if raw_pin_time is None else int(raw_pin_time)


def save_graph_pin(user: LoggedInUser, pin_time: int | None) -> None:
    user.save_file(GRAPH_PIN_USER_FILE, pin_time)
