#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the GUI and the daemon accept as a map's name.

Map names are URL components, file names and per-map permission idents
(``map.<name>``), so both sides restrict them to the same safe charset and length.
"""

from typing import Final

MAP_NAME_MAX_LENGTH: Final = 100
MAP_NAME_PATTERN: Final = r"^[a-zA-Z0-9_\-]+$"
