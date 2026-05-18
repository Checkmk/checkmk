#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define repository interfaces for fetching from data sources.

These are intentionally only protocols as they are meant to only signify what sort of domain data
they will return. This allows us to pass stubs when testing our applications.
"""

from collections.abc import Sequence
from typing import Protocol

from ._models import Host


class HostRepository(Protocol):
    def fetch(self, *, limit: int) -> Sequence[Host]:
        """Fetch hosts based on filter criteria."""
        ...

    def count(self) -> int:
        """Count the total number of hosts."""
        ...
