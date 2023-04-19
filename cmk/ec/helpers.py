#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import threading
from logging import Logger
from types import TracebackType
from typing import Literal


class ECLock:
    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger
        self._lock = threading.Lock()

    def __enter__(self) -> None:
        self._logger.debug("[%s] Trying to acquire lock", threading.current_thread().name)
        self._lock.acquire()
        self._logger.debug("[%s] Acquired lock", threading.current_thread().name)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        self._logger.debug("[%s] Releasing lock", threading.current_thread().name)
        self._lock.release()
        return False  # Do not swallow exceptions
