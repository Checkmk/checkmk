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
from typing import Any, DefaultDict, Dict, Iterable, Iterator, List

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
prev_snapshot: Snapshot = Snapshot.null()
phase_stack: List[str] = []


def reset():
    global times
    global prev_snapshot
    global phase_stack
    times.clear()
    prev_snapshot = Snapshot.null()
    phase_stack.clear()


def _start(initial_phase: str) -> None:
    global times, prev_snapshot
    console.vverbose("[cpu_tracking] Start with phase '%s'\n" % initial_phase)
    times.clear()
    prev_snapshot = Snapshot.take()

    phase_stack[:] = [initial_phase]


def _end(phase_name: str) -> None:
    console.vverbose("[cpu_tracking] End\n")
    _add_times_to_phase(phase_name, Snapshot.take())
    phase_stack.clear()


def _push_phase(phase_name: str) -> None:
    if not is_tracking():
        return

    console.vverbose("[cpu_tracking] Push phase '%s' (Stack: %r)\n" % (phase_name, phase_stack))
    _add_times_to_phase(phase_stack[-1], Snapshot.take())
    phase_stack.append(phase_name)


def _pop_phase(phase_name: str) -> None:
    if not is_tracking():
        return

    console.vverbose("[cpu_tracking] Pop phase '%s' (Stack: %r)\n" % (phase_stack[-1], phase_stack))
    _add_times_to_phase(phase_name, Snapshot.take())
    phase_stack.pop()


def get_times() -> Dict[str, Snapshot]:
    return times


def is_tracking() -> bool:
    return bool(phase_stack)


def _add_times_to_phase(phase_name: str, snapshot: Snapshot) -> None:
    global prev_snapshot
    for pn in phase_name, "TOTAL":
        times[pn] += snapshot - prev_snapshot
    prev_snapshot = snapshot


def update(cpu_times: Dict[str, Snapshot]):
    for name, value_list in cpu_times.items():
        times[name] += value_list


@contextlib.contextmanager
def phase(phase_name: str) -> Iterator[None]:
    _push_phase(phase_name)
    try:
        yield
    finally:
        _pop_phase(phase_name)


@contextlib.contextmanager
def execute(name: str) -> Iterator[None]:
    reset()
    _start(name)
    try:
        yield
    finally:
        _end(name)
