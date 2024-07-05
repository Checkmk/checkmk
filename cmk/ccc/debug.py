#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

debug_mode = False


def enabled() -> bool:
    return debug_mode


def enable() -> None:
    global debug_mode
    debug_mode = True


def disable() -> None:
    global debug_mode
    debug_mode = False
