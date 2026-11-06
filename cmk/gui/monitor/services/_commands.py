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

from cmk.ccc.user import UserId
from cmk.gui.livestatus_utils.commands.downtimes import RecurMode
from cmk.gui.monitor.command import ModifiableAttribute

from ._models import RescheduleTarget, ServiceTarget


class ServiceRescheduler(Protocol):
    def reschedule(self, targets: Sequence[RescheduleTarget]) -> None:
        """Force an immediate active check for each target on its site."""
        ...


class ServiceNotifier(Protocol):
    def send_custom_notification(
        self,
        targets: Sequence[ServiceTarget],
        *,
        author: UserId,
        comment: str,
        forced: bool,
        broadcast: bool,
    ) -> None:
        """Let the core send a custom notification for each target on its site."""
        ...


class ServiceCheckResultFaker(Protocol):
    def fake_check_result(
        self, targets: Sequence[ServiceTarget], *, state: int, output: str
    ) -> None:
        """Submit a check result for each target on its site, as if its check had run."""
        ...


class ServiceAttributeModifier(Protocol):
    def toggle_attribute(
        self, targets: Sequence[ServiceTarget], attribute: ModifiableAttribute, *, enabled: bool
    ) -> None:
        """Enable or disable the attribute for each target on its site."""
        ...

    def reset_modified_attributes(self, targets: Sequence[ServiceTarget]) -> None:
        """Undo what such toggles changed for each target, back to its configuration."""
        ...


class ServiceAcknowledger(Protocol):
    def acknowledge(
        self,
        targets: Sequence[ServiceTarget],
        *,
        author: UserId,
        comment: str,
        sticky: bool,
        persistent: bool,
        notify: bool,
        expire_on: dt.datetime | None,
    ) -> int:
        """Acknowledge each visible target with a problem on its site, returning how many.

        Raises ServiceNotFoundError if none of the targets is found.
        """
        ...

    def remove_acknowledgements(self, targets: Sequence[ServiceTarget]) -> int:
        """Remove the acknowledgement of each visible target on its site, returning how many."""
        ...


class ServiceDowntimeScheduler(Protocol):
    def schedule_downtime(
        self,
        targets: Sequence[ServiceTarget],
        *,
        author: UserId,
        comment: str,
        start_time: dt.datetime,
        end_time: dt.datetime,
        recur: RecurMode,
        duration_minutes: int,
    ) -> int:
        """Schedule a downtime for each visible target on its site, returning how many.

        Raises ServiceNotFoundError if none of the targets is found.
        """
        ...

    def remove_downtimes(self, targets: Sequence[ServiceTarget]) -> int:
        """Remove the downtimes of the targets on their sites, returning for how many."""
        ...
