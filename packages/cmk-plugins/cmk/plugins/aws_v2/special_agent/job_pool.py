#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import threading
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from types import TracebackType
from typing import Self


class JobPool:
    """A thread pool that never queues jobs ahead of its free threads.

    submit() blocks until a thread is free. What the caller prepares for a job, such as the
    credentials of an assumed role that last one hour, is therefore used soon after, not
    after a long queue of other jobs.
    """

    def __init__(self, size: int) -> None:
        self._executor = ThreadPoolExecutor(max_workers=size)
        self._slots = threading.BoundedSemaphore(size)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._executor.shutdown(wait=True)

    @contextmanager
    def slot(self) -> Iterator[None]:
        """A slot for work that runs in the calling thread."""
        with self._slots:
            yield

    def submit[**P, T](
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> Future[T]:
        self._slots.acquire()
        future = self._executor.submit(function, *args, **kwargs)
        future.add_done_callback(lambda _: self._slots.release())
        return future
