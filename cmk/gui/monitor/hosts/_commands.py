#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Define command interfaces for performing server-side actions.

Each command should have a skinny interface for easy testing. One interface for each command group.
"""

from collections.abc import Sequence
from typing import Protocol

from ._models import RescheduleTarget


class HostRescheduler(Protocol):
    def reschedule(self, targets: Sequence[RescheduleTarget]) -> None:
        """Force an immediate active check for each target on its site."""
        ...
