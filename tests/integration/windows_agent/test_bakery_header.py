#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from pathlib import Path

from cmk.bakery.internal import AGENT_FILE_HEADER


def test_kbakerymarker_is_the_first_line_of_agent_file_header() -> None:
    """IsBakeryIni() in agents/wnx/src/engine/upgrade.cpp recognises a baked
    file by kBakeryMarker at its start."""
    upgrade_h = Path(os.environ["UPGRADE_H"])
    marker = re.search(r'kBakeryMarker =\s*"([^"]*)";', upgrade_h.read_text())

    assert marker is not None, f"{upgrade_h} defines no kBakeryMarker"
    assert AGENT_FILE_HEADER.splitlines()[0] == marker.group(1)
