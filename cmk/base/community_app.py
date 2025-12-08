#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition

from .base_app import CheckmkBaseApp
from .modes.check_mk import common_modes, general_options
from .modes.modes import Modes


def make_app() -> CheckmkBaseApp:
    return CheckmkBaseApp(
        edition=Edition.COMMUNITY,
        modes=_modes(),
    )


def _modes() -> Modes:
    modes = Modes()

    for option in general_options():
        modes.register_general_option(option)

    for mode in common_modes():
        modes.register(mode)

    return modes
