#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from logging import Logger

from .helpers import ECLock
from .query import Columns


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b with weight t."""
    return (1 - t) * a + t * b


class Perfcounters:
    """Helper class for performance counting."""

    _counter_names: Sequence[str] = [
        "messages",
        "rule_tries",
        "rule_hits",
        "drops",
        "overflows",
        "events",
        "connects",
    ]

    # Average processing times
    _weights: Mapping[str, float] = {
        "processing": 0.99,  # event processing
        "sync": 0.95,  # Replication sync
        "request": 0.95,  # Client requests
    }

    # TODO: Why aren't self._times / self._rates / ... not initialized with their defaults?
    def __init__(self, logger: Logger) -> None:
        self._lock = ECLock(logger)

        # Initialize counters
        self._counters = {n: 0 for n in self._counter_names}
        self._old_counters: dict[str, int] = {}
        self._rates: dict[str, float] = {}
        self._average_rates: dict[str, float] = {}
        self._times: dict[str, float] = {}
        self._last_statistics: float | None = None

        self._logger = logger.getChild("Perfcounters")

    def count(self, counter: str) -> None:
        with self._lock:
            self._counters[counter] += 1

    def count_time(self, counter: str, ptime: float) -> None:
        with self._lock:
            if counter in self._times:
                self._times[counter] = lerp(ptime, self._times[counter], self._weights[counter])
            else:
                self._times[counter] = ptime

    def do_statistics(self) -> None:
        with self._lock:
            now = time.time()
            duration = now - self._last_statistics if self._last_statistics else 0
            for name, value in self._counters.items():
                if duration:
                    delta = value - self._old_counters[name]
                    rate = delta / duration
                    self._rates[name] = rate
                    if name in self._average_rates:
                        # We could make the weight configurable
                        self._average_rates[name] = lerp(rate, self._average_rates[name], 0.9)
                    else:
                        self._average_rates[name] = rate

            self._last_statistics = now
            self._old_counters = self._counters.copy()

    @classmethod
    def status_columns(cls: type[Perfcounters]) -> Columns:
        columns: list[tuple[str, float]] = []
        # Please note: status_columns() and get_status() need to produce lists with exact same column order
        for name in cls._counter_names:
            columns.extend(
                [
                    (f"status_{name}", 0),
                    (f"status_{name.rstrip('s')}_rate", 0.0),
                    (f"status_average_{name.rstrip('s')}_rate", 0.0),
                ]
            )

        for name in cls._weights:
            columns.append((f"status_average_{name}_time", 0.0))

        return columns

    def get_status(self) -> Sequence[float]:
        with self._lock:
            row: list[float] = []
            # Please note: status_columns() and get_status() need to produce lists with exact same column order
            for name in self._counter_names:
                row.extend(
                    [
                        self._counters[name],
                        self._rates.get(name, 0.0),
                        self._average_rates.get(name, 0.0),
                    ]
                )

            for name in self._weights:
                row.append(self._times.get(name, 0.0))

            return row
