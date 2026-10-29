#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the daemon asks the GUI about the names of map links at most."""

from typing import Final

# Linked maps resolved in one state fetch, so a web of links stays bounded. A
# link beyond them is pending and marked stale.
LINKED_MAPS_MAX: Final = 256
# Held maps the daemon names per question; one left out only comes with its config.
CACHED_MAP_REFS_MAX: Final = 1024
