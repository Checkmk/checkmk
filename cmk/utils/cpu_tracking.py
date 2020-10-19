#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import functools
import os
import posix
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, DefaultDict, Dict, Iterable, Iterator, List, Tuple

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
last_time_snapshot: Snapshot = Snapshot.null()
phase_stack: List[str] = []

# TODO (sk) make private low level API: reset, start, end


def reset():
    global times
    global last_time_snapshot
    global phase_stack
    times.clear()
    last_time_snapshot = Snapshot.null()
    phase_stack = []


def start(initial_phase: str) -> None:
    global times, last_time_snapshot
    console.vverbose("[cpu_tracking] Start with phase '%s'\n" % initial_phase)
    times.clear()
    last_time_snapshot = Snapshot.take()

    del phase_stack[:]
    phase_stack.append(initial_phase)


def end() -> None:
    console.vverbose("[cpu_tracking] End\n")
    _add_times_to_phase()
    del phase_stack[:]


def push_phase(phase_name: str) -> None:
    if _is_not_tracking():
        return

    console.vverbose("[cpu_tracking] Push phase '%s' (Stack: %r)\n" % (phase_name, phase_stack))
    _add_times_to_phase()
    phase_stack.append(phase_name)


def pop_phase() -> None:
    if _is_not_tracking():
        return

    console.vverbose("[cpu_tracking] Pop phase '%s' (Stack: %r)\n" % (phase_stack[-1], phase_stack))
    _add_times_to_phase()
    del phase_stack[-1]


def get_times() -> Dict[str, Snapshot]:
    return times


def _is_not_tracking() -> bool:
    return not bool(phase_stack)


def _add_times_to_phase() -> None:
    global last_time_snapshot
    new_time_snapshot = Snapshot.take()
    for phase_name in phase_stack[-1], "TOTAL":
        times[phase_name] += new_time_snapshot - last_time_snapshot
    last_time_snapshot = new_time_snapshot


def track(method: Callable) -> Callable:
    """Decorator to track CPU in methods."""
    @functools.wraps(method)
    def wrapper(self: Any, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> None:
        push_phase(self.cpu_tracking_id)
        try:
            return method(self, *args, **kwargs)
        finally:
            pop_phase()

    return wrapper


def update(cpu_times: Dict[str, Snapshot]):
    for name, value_list in cpu_times.items():
        times[name] += value_list


@contextlib.contextmanager
def phase(phase_name: str) -> Iterator[None]:
    push_phase(phase_name)
    try:
        yield
    finally:
        pop_phase()


@contextlib.contextmanager
def execute(name: str) -> Iterator[None]:
    reset()
    start(name)
    try:
        yield
    finally:
        end()
