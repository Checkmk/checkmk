#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.ctx_stack import g
from cmk.gui.htmllib.html import html


def play_alarm_sounds(
    *,
    enable_sounds: bool,
    sounds: Sequence[tuple[str, str]],
    sound_url: str,
) -> None:
    if not enable_sounds or not sounds:
        return

    if "alarm_sound_states" not in g:
        return

    url = sound_url
    if not url.endswith("/"):
        url += "/"

    for state_name, wav in sounds:
        if not state_name or state_name in g.alarm_sound_states:
            html.play_sound(url + wav)
            break  # only one sound at one time
