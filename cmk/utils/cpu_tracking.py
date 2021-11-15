#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
import posix
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from cmk.utils.log import console

__all__ = ["CPUTracker", "Snapshot", "times_result"]


def times_result(seq: Iterable[float]) -> posix.times_result:
    # mypy warnings are false positives.
    return posix.times_result(tuple(seq))  # type: ignore[arg-type, call-arg]


@dataclass(frozen=True)
class Snapshot:
    process: posix.times_result

    @property
    def idle(self) -> float:
        return max(self.process.elapsed - sum(self.process[:4]), 0.0)

    @classmethod
    def null(cls):
        return cls(times_result((0.0, 0.0, 0.0, 0.0, 0.0)))

    @classmethod
    def take(cls) -> Snapshot:
        return cls(os.times())

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> Snapshot:
        try:
            return cls(times_result(serialized["process"]))
        except LookupError as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> Mapping[str, Any]:
        return {"process": tuple(self.process)}

    def __add__(self, other: Snapshot) -> Snapshot:
        if not isinstance(other, Snapshot):
            return NotImplemented
        return Snapshot(times_result(t0 + t1 for t0, t1 in zip(self.process, other.process)))

    def __sub__(self, other: Snapshot) -> Snapshot:
        if not isinstance(other, Snapshot):
            return NotImplemented
        return Snapshot(times_result(t0 - t1 for t0, t1 in zip(self.process, other.process)))

    def __bool__(self) -> bool:
        return self != Snapshot.null()


class CPUTracker:
    def __init__(self) -> None:
        super().__init__()
        self._start: Snapshot = Snapshot.null()
        self._end: Snapshot = Snapshot.null()

    def __repr__(self) -> str:
        return "%s()" % type(self).__name__

    def __enter__(self):
        self._start = Snapshot.take()
        console.vverbose("[cpu_tracking] Start [%x]\n", id(self))
        return self

    def __exit__(self, *exc_info):
        self._end = Snapshot.take()
        console.vverbose("[cpu_tracking] Stop [%x - %s]\n", id(self), self.duration)

    @property
    def duration(self) -> Snapshot:
        return self._end - self._start
