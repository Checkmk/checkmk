#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Define command interfaces for performing server-side actions.

Each command should have a skinny interface for easy testing. One interface for each command group.
"""

import datetime as dt
from collections.abc import Sequence
from typing import Protocol

from ._models import HostTarget


class HostRescheduler(Protocol):
    def reschedule(
        self, targets: Sequence[HostTarget], *, start: dt.datetime, spread: dt.timedelta
    ) -> int:
        """Force an active check for each visible target on its site, returning how many.

        The checks are spread evenly from start over the given span.
        """
        ...
