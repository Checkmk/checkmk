#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.ccc.version import Edition

from .modes.modes import Modes


class CheckmkBaseApp:
    """Provide features to the runtime

    Hold the features available to the runtime based on the context (edition) the app is created for.
    """

    def __init__(self, edition: Edition, modes: Modes) -> None:
        self.edition: Final = edition
        self.modes: Final = modes
