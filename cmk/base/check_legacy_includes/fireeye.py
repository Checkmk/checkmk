#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


def check_fireeye_states(states: list[tuple[str, str]]) -> dict[str, tuple[int, str]]:
    # Now we only known the OK states and health states
    # but we can expand if we know more
    map_states = {
        "status": {
            "good": (0, "good"),
            "ok": (0, "OK"),
        },
        "disk status": {
            "online": (0, "online"),
        },
        "health": {
            "1": (0, "healthy"),
            "2": (2, "unhealthy"),
        },
    }
    states_evaluated: dict = {}
    for what, text in states:
        states_evaluated.setdefault(
            text, map_states[text.lower()].get(what.lower(), (2, "not %s" % what.lower()))
        )

    return states_evaluated
