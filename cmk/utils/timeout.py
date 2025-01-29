#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import signal
from types import FrameType
from typing import Final, NoReturn

from cmk.ccc.exceptions import MKTimeout

__all__ = ["MKTimeout", "Timeout"]


class Timeout:
    def __init__(self, timeout: int, *, message: str) -> None:
        self.timeout: Final = timeout
        self.message: Final = message
        self._signaled = False

    @property
    def signaled(self) -> bool:
        return self._signaled

    def _handler(self, signum: int, frame: FrameType | None) -> NoReturn:
        self._signaled = True
        raise MKTimeout(self.message)

    def __enter__(self) -> Timeout:
        self._signaled = False
        signal.signal(signal.SIGALRM, self._handler)
        signal.alarm(self.timeout)
        return self

    def __exit__(self, *exc_info: object) -> None:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        signal.alarm(0)
