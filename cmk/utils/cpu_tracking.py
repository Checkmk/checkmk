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
from typing import Any, DefaultDict, Dict, Iterable, Iterator, Mapping, MutableMapping, Optional

from cmk.utils.log import console

__all__ = ["CPUTracker", "phase", "Snapshot", "times_result"]


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


class CPUTracker(MutableMapping[str, Snapshot]):
    def __init__(self, tracker: Optional[Mapping[str, Snapshot]] = None) -> None:
        super().__init__()
        self._times: DefaultDict[str, Snapshot] = defaultdict(Snapshot.null)
        for phase_name, snapshot in tracker.items() if tracker else ():
            self._times[phase_name] = snapshot

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, dict(self._times))

    def serialize(self) -> Dict[str, Any]:
        return {phase_name: snapshot.serialize() for phase_name, snapshot in self.items()}

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "CPUTracker":
        return cls({
            phase_name: Snapshot.deserialize(snapshot)
            for phase_name, snapshot in serialized.items()
        })

    def __getitem__(self, phase_name: str) -> Snapshot:
        return self._times.__getitem__(phase_name)

    def __setitem__(self, phase_name: str, snapshot: Snapshot) -> None:
        return self._times.__setitem__(phase_name, snapshot)

    def __delitem__(self, phase_name: str) -> None:
        return self._times.__delitem__(phase_name)

    def __iter__(self) -> Iterator[str]:
        return self._times.__iter__()

    def __len__(self) -> int:
        return self._times.__len__()

    def clear(self) -> None:
        return self._times.clear()


@contextlib.contextmanager
def phase(tracker: CPUTracker, phase_name: str) -> Iterator[None]:
    console.vverbose("[cpu_tracking] Start %r\n", phase_name)
    start = Snapshot.take()
    try:
        yield
    finally:
        console.vverbose("[cpu_tracking] Stop %r\n", phase_name)
        tracker[phase_name] += Snapshot.take() - start
