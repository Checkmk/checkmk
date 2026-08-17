#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The intervals a scheduled downtime may repeat on.

Repeating a downtime is the core's work, so which intervals exist is the edition's word. An
edition says so where it registers its downtime command, and the intervals are read back out
of that command rather than handed in a second time: what a panel offers and what the classic
view's dropdown offers are one list, and cannot part ways.

The command is found by carrying the intervals rather than by name, so this domain needs to
know nothing about the legacy commands beyond what it reads off them.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cmk.gui.livestatus_utils.commands.downtimes import RecurMode


@dataclass(frozen=True, kw_only=True)
class DowntimeRecurrence:
    recur: RecurMode
    title: str


class LegacyRecurringDowntimes(Protocol):
    def recurrences(self) -> Sequence[DowntimeRecurrence]: ...


@runtime_checkable
class LegacyDowntimeCommand(Protocol):
    @property
    def recurring_downtimes(self) -> LegacyRecurringDowntimes: ...


class DowntimeCommandSource(Protocol):
    def values(self) -> Iterable[object]: ...


class DowntimeRecurrences:
    def __init__(self) -> None:
        self._legacy: DowntimeCommandSource | None = None

    def use_legacy_source(self, source: DowntimeCommandSource) -> None:
        self._legacy = source

    def offered(self) -> Sequence[DowntimeRecurrence]:
        # Read on demand rather than at wiring time, so the titles are translated for the user
        # asking and an edition registering its command later is still picked up.
        if self._legacy is None:
            return []
        for command in self._legacy.values():
            if isinstance(command, LegacyDowntimeCommand):
                return command.recurring_downtimes.recurrences()
        return []


downtime_recurrences = DowntimeRecurrences()
