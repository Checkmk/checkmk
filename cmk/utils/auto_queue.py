#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
import time
from collections.abc import Callable, Container, Iterable, Iterator, Sequence
from pathlib import Path
from types import FrameType, TracebackType
from typing import Final, NoReturn, TypeVar

from cmk.utils.exceptions import MKException
from cmk.utils.log import console
from cmk.utils.type_defs import HostName

_T = TypeVar("_T")


class _Timeout(MKException):
    pass


class TimeLimitFilter:
    @classmethod
    def _raise_timeout(cls, signum: int, stack_frame: FrameType | None) -> NoReturn:
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
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
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


class AutoQueue(Iterable[HostName]):
    @staticmethod
    def _host_name(file_path: Path) -> HostName:
        return HostName(file_path.name)

    def __init__(self, directory: Path | str) -> None:
        self._dir = Path(directory)

    def _ls(self) -> Sequence[Path]:
        try:
            # we must consume the .iterdir generator to make sure
            # the FileNotFoundError gets raised *here*.
            return list(self._dir.iterdir())
        except FileNotFoundError:
            return ()

    def __len__(self) -> int:
        return len(self._ls())

    def __iter__(self) -> Iterator[HostName]:
        return (self._host_name(f) for f in self._ls()).__iter__()

    def oldest(self) -> float | None:
        return min((f.stat().st_mtime for f in self._ls()), default=None)

    def remove(self, host_name: HostName) -> None:
        (self._dir / str(host_name)).unlink(missing_ok=True)

    def cleanup(self, *, valid_hosts: Container[HostName], logger: Callable[[str], None]) -> None:
        for host_name in (hn for f in self._ls() if (hn := self._host_name(f)) not in valid_hosts):
            logger(f"  Removing mark '{host_name}' (host not configured)\n")
            self.remove(host_name)
