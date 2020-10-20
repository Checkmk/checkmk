#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import os
import posix
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, Iterable, Iterator

from cmk.utils.log import console

# TODO: Move state out of module scope
# TODO: This should be rewritten to a context manager object. See cmk.utils.profile for
#       an example how it could look like.


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


times: DefaultDict[str, Snapshot] = defaultdict(Snapshot.null)
_running: bool = False


def reset():
    global times
    times.clear()


def get_times() -> Dict[str, Snapshot]:
    return times


def is_tracking() -> bool:
    return _running


def update(cpu_times: Dict[str, Snapshot]):
    for name, value_list in cpu_times.items():
        times[name] += value_list


@contextlib.contextmanager
def phase(phase_name: str) -> Iterator[None]:
    console.vverbose("[cpu_tracking] Push phase %r\n", phase_name)
    start = Snapshot.take()
    try:
        yield
    finally:
        console.vverbose("[cpu_tracking] Pop phase %r\n", phase_name)
        delta = Snapshot.take() - start
        if is_tracking():
            times[phase_name] += delta


@contextlib.contextmanager
def execute(phase_name: str) -> Iterator[None]:
    assert not is_tracking(), "tracking already started"
    console.vverbose("[cpu_tracking] Start with phase %r\n", phase_name)

    global _running
    _running = True
    reset()
    times.clear()
    start = Snapshot.take()
    try:
        yield
    finally:
        console.vverbose("[cpu_tracking] End\n")
        _running = False
        delta = Snapshot.take() - start
        times[phase_name] += delta
