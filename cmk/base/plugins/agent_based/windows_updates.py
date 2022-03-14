#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import NamedTuple, Optional, Sequence

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


class Section(NamedTuple):
    reboot_required: bool
    important_updates: Sequence[str]
    optional_updates: Sequence[str]
    forced_reboot: Optional[float]


def parse_windows_updates(string_table: StringTable) -> Optional[Section]:
    if not string_table or len(string_table[0]) != 3:
        return None

    if string_table[0][0] == "x":
        raise RuntimeError(" ".join(string_table[1]))

    important_updates_count = int(string_table[0][1])
    optional_updates_count = int(string_table[0][2])

    lines_iter = iter(string_table[1:])

    important = (
        [u.strip() for u in " ".join(next(lines_iter)).split(";")]
        if important_updates_count
        else []
    )
    optional = (
        [u.strip() for u in " ".join(next(lines_iter)).split(";")] if optional_updates_count else []
    )

    try:
        forced_reboot: Optional[float] = time.mktime(
            time.strptime(" ".join(next(lines_iter)), "%Y-%m-%d %H:%M:%S")
        )
    except (StopIteration, ValueError):
        forced_reboot = None

    return Section(
        reboot_required=bool(int(string_table[0][0])),
        important_updates=important,
        optional_updates=optional,
        forced_reboot=forced_reboot,
    )


register.agent_section(
    name="windows_updates",
    parse_function=parse_windows_updates,
)
