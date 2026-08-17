#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from cmk.gui.monitor.command import DowntimeRecurrence, DowntimeRecurrences


class _LegacyRecurringDowntimes:
    """Stands in for what an edition hands its downtime command."""

    def __init__(self, titles: Iterable[str]) -> None:
        self._titles = iter(titles)

    def recurrences(self) -> Sequence[DowntimeRecurrence]:
        return [DowntimeRecurrence(recur="fixed", title=next(self._titles))]


class _LegacyCommand:
    """Shaped like a view command, without importing that layer."""

    def __init__(self, recurring_downtimes: _LegacyRecurringDowntimes) -> None:
        self.recurring_downtimes = recurring_downtimes


class _OtherLegacyCommand:
    def __init__(self) -> None:
        self.ident = "acknowledge"


class _LegacySource:
    def __init__(self, commands: Sequence[object]) -> None:
        self._commands = commands

    def values(self) -> Iterable[object]:
        return self._commands


def _recurrences(commands: Sequence[object]) -> DowntimeRecurrences:
    recurrences = DowntimeRecurrences()
    recurrences.use_legacy_source(_LegacySource(commands))
    return recurrences


def test_nothing_repeats_until_a_source_is_wired() -> None:
    assert list(DowntimeRecurrences().offered()) == []


def test_the_intervals_of_the_registered_downtime_command_are_the_ones_on_offer() -> None:
    recurrences = _recurrences([_LegacyCommand(_LegacyRecurringDowntimes(["never"]))])

    assert list(recurrences.offered()) == [DowntimeRecurrence(recur="fixed", title="never")]


def test_a_registry_without_a_downtime_command_offers_nothing() -> None:
    assert list(_recurrences([_OtherLegacyCommand()]).offered()) == []


def test_the_command_is_found_among_the_others_the_registry_holds() -> None:
    commands = [_OtherLegacyCommand(), _LegacyCommand(_LegacyRecurringDowntimes(["never"]))]

    assert [recurrence.recur for recurrence in _recurrences(commands).offered()] == ["fixed"]


def test_the_source_is_read_per_call_so_a_title_is_translated_for_who_asks() -> None:
    recurrences = _recurrences([_LegacyCommand(_LegacyRecurringDowntimes(["never", "nie"]))])

    assert [recurrence.title for recurrence in recurrences.offered()] == ["never"]
    assert [recurrence.title for recurrence in recurrences.offered()] == ["nie"]
