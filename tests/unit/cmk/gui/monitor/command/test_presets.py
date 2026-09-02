#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from cmk.gui.config import Config
from cmk.gui.monitor.command import acknowledge_defaults, downtime_presets


def test_acknowledge_defaults_follow_the_setting(load_config: Config) -> None:
    config = dataclasses.replace(
        load_config,
        acknowledge_problems={
            "ack_sticky": True,
            "ack_notify": False,
            "ack_persistent": True,
            "ack_expire": 7200,
        },
    )

    defaults = acknowledge_defaults(config)

    assert (defaults.sticky, defaults.persistent, defaults.notify, defaults.expire_seconds) == (
        True,
        True,
        False,
        7200,
    )


def test_the_expiry_falls_back_the_way_the_classic_form_does(load_config: Config) -> None:
    """`ack_expire` is absent from the setting's default, so there is nothing to read."""
    config = dataclasses.replace(
        load_config,
        acknowledge_problems={"ack_sticky": False, "ack_notify": True, "ack_persistent": False},
    )

    assert acknowledge_defaults(config).expire_seconds == 3600


def test_downtime_presets_carry_both_kinds_of_end(load_config: Config) -> None:
    """The two kinds share one slot, the way the setting stores them."""
    config = dataclasses.replace(
        load_config,
        user_downtime_timeranges=[
            {"title": "2 hours", "end": 7200},
            {"title": "Today", "end": "next_day"},
        ],
    )

    presets = downtime_presets(config)

    assert [(preset.title, preset.end) for preset in presets] == [
        ("2 hours", 7200),
        ("Today", "next_day"),
    ]


def test_an_end_the_panel_cannot_render_is_left_out(load_config: Config) -> None:
    """Offering a duration that resolves to no time would be worse than not offering it."""
    config = dataclasses.replace(
        load_config,
        user_downtime_timeranges=[
            {"title": "Fine", "end": 3600},
            {"title": "Nonsense", "end": "next_century"},
        ],
    )

    assert [preset.title for preset in downtime_presets(config)] == ["Fine"]
