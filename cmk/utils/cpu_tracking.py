#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import posix
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable

from cmk.utils.log import console

__all__ = ["CPUTracker", "Snapshot", "times_result"]


def times_result(seq: Iterable[float]) -> posix.times_result:
    # mypy warnings are false positives.
    return posix.times_result(tuple(seq))  # type: ignore[arg-type, call-arg]


@dataclass(frozen=True)
class Snapshot:
    process: posix.times_result
    run_time: float

    @classmethod
    def null(cls):
        return cls(
            times_result((0.0, 0.0, 0.0, 0.0, 0.0)),
            0.0,
        )

    @classmethod
    def take(cls) -> "Snapshot":
        return cls(os.times(), time.time())

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "Snapshot":
        try:
            return cls(
                times_result(serialized["process"]),
                serialized["run_time"],
            )
        except LookupError as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> Dict[str, Any]:
        return {"process": tuple(self.process), "run_time": self.run_time}

    def __add__(self, other: "Snapshot") -> "Snapshot":
        if not isinstance(other, Snapshot):
            return NotImplemented
        return Snapshot(
            times_result(t0 + t1 for t0, t1 in zip(self.process, other.process)),
            self.run_time + other.run_time,
        )

    def __sub__(self, other: "Snapshot") -> "Snapshot":
        if not isinstance(other, Snapshot):
            return NotImplemented
        return Snapshot(
            times_result(t0 - t1 for t0, t1 in zip(self.process, other.process)),
            self.run_time - other.run_time,
        )


class CPUTracker:
    def __init__(self) -> None:
        super().__init__()
        self._start: Snapshot = Snapshot.null()
        self._end: Snapshot = Snapshot.null()

    def __repr__(self) -> str:
        return "%s()" % type(self).__name__

    def __enter__(self):
        console.vverbose("[cpu_tracking] Start\n")
        self._start = Snapshot.take()
        return self

    def __exit__(self, *exc_info):
        console.vverbose("[cpu_tracking] Stop\n")
        self._end = Snapshot.take()

    def serialize(self) -> Dict[str, Any]:
        return {
            "start": self._start.serialize(),
            "end": self._end.serialize(),
        }

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "CPUTracker":
        try:
            tracker = CPUTracker()
            tracker._start = Snapshot.deserialize(serialized["start"])
            tracker._end = Snapshot.deserialize(serialized["end"])
            return tracker
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    @property
    def duration(self) -> Snapshot:
        return self._end - self._start
