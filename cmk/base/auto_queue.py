#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
import time
from contextlib import suppress
from pathlib import Path
from types import FrameType, TracebackType
from typing import (
    Callable,
    Container,
    Final,
    Iterable,
    NoReturn,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
)

import livestatus

from cmk.utils.exceptions import MKException
from cmk.utils.log import console
from cmk.utils.type_defs import HostName

_T = TypeVar("_T")


class _Timeout(MKException):
    pass


class TimeLimitFilter:
    @classmethod
    def _raise_timeout(cls, signum: int, stack_frame: Optional[FrameType]) -> NoReturn:
        raise _Timeout()

    def __init__(
        self,
        *,
        limit: int,
        grace: int,
        label: str = "elements",
    ) -> None:
        self._start = int(time.monotonic())
        self._end = self._start + limit
        self.limit: Final = limit
        self.label: Final = label

        signal.signal(signal.SIGALRM, TimeLimitFilter._raise_timeout)
        signal.alarm(self.limit + grace)

    def __enter__(self) -> "TimeLimitFilter":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        signal.alarm(0)
        if isinstance(exc_val, _Timeout):
            console.verbose(
                f"  Timeout of {self.limit} seconds reached. "
                f"Let's do the remaining {self.label} next time."
            )
            return True
        return False

    def __call__(self, iterable: Iterable[_T]) -> Iterable[_T]:
        for element in iterable:
            yield element
            if time.monotonic() > self._end:
                raise _Timeout()


class AutoQueue:
    @staticmethod
    def _host_name(file_path: Path) -> HostName:
        return HostName(file_path.name)

    def _file_path(self, host_name: HostName) -> Path:
        return self._dir / str(host_name)

    def __init__(self, directory: Path | str) -> None:
        self._dir = Path(directory)

    def _ls(self) -> Sequence[Path]:
        try:
            # we must consume the .iterdir generator to make sure
            # the FileNotFoundError gets raised *here*.
            return list(self._dir.iterdir())
        except FileNotFoundError:
            return []

    def __len__(self) -> int:
        return len(self._ls())

    def oldest(self) -> Optional[float]:
        return min((f.stat().st_mtime for f in self._ls()), default=None)

    def queued_hosts(self) -> Iterable[HostName]:
        return (self._host_name(f) for f in self._ls())

    def add(self, host_name: HostName) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file_path(host_name).touch()

    def remove(self, host_name: HostName) -> None:
        with suppress(FileNotFoundError):
            self._file_path(host_name).unlink()

    def cleanup(self, *, valid_hosts: Container[HostName], logger: Callable[[str], None]) -> None:
        for host_name in (hn for f in self._ls() if (hn := self._host_name(f)) not in valid_hosts):
            logger(f"  Removing mark '{host_name}' (host not configured)\n")
            self.remove(host_name)


def get_up_hosts() -> Optional[Set[HostName]]:
    query = "GET hosts\nColumns: name state"
    try:
        response = livestatus.LocalConnection().query(query)
        return {HostName(name) for name, state in response if state == 0}
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        pass
    return None
