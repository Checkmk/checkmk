#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
import posix
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Snapshot:
    process: posix.times_result

    @property
    def idle(self) -> float:
        return max(self.process.elapsed - sum(self.process[:4]), 0.0)

    @classmethod
    def null(cls) -> Snapshot:
        return cls(posix.times_result((0.0, 0.0, 0.0, 0.0, 0.0)))

    @classmethod
    def take(cls) -> Snapshot:
        return cls(os.times())

    @classmethod
    def deserialize(cls, serialized: object) -> Snapshot:
        try:
            assert isinstance(serialized, dict)
            return cls(posix.times_result(serialized["process"]))
        except LookupError as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> object:
        return {"process": tuple(self.process)}

    def __add__(self, other: Snapshot) -> Snapshot:
        if not isinstance(other, Snapshot):
            return NotImplemented
        return Snapshot(posix.times_result(t0 + t1 for t0, t1 in zip(self.process, other.process)))

    def __sub__(self, other: Snapshot) -> Snapshot:
        if not isinstance(other, Snapshot):
            return NotImplemented
        return Snapshot(posix.times_result(t0 - t1 for t0, t1 in zip(self.process, other.process)))

    def __bool__(self) -> bool:
        return self != Snapshot.null()


class CPUTracker:
    def __init__(self, log: Callable[[str], None]) -> None:
        super().__init__()
        self._log = log
        self._start: Snapshot = Snapshot.null()
        self._end: Snapshot = Snapshot.null()

    def __repr__(self) -> str:
        return "%s()" % type(self).__name__

    def __enter__(self) -> CPUTracker:
        self._start = Snapshot.take()
        self._log(f"[cpu_tracking] Start [{id(self):x}]")
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._end = Snapshot.take()
        self._log(f"[cpu_tracking] Stop [{id(self):x} - {self.duration}]")

    @property
    def duration(self) -> Snapshot:
        return self._end - self._start
