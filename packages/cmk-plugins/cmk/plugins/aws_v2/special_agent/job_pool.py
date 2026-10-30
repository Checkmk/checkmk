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

    Once a job raises, submit() and slot() raise its exception, so no new work starts. The
    jobs that are already running still finish.
    """

    def __init__(self, size: int) -> None:
        self._executor = ThreadPoolExecutor(max_workers=size)
        self._slots = threading.BoundedSemaphore(size)
        self._failure: BaseException | None = None

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
        self._take_slot()
        try:
            yield
        finally:
            self._slots.release()

    def submit[**P, T](
        self, function: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> Future[T]:
        self._take_slot()
        future = self._executor.submit(function, *args, **kwargs)
        future.add_done_callback(self._job_done)
        return future

    def _take_slot(self) -> None:
        self._slots.acquire()
        if self._failure is not None:
            self._slots.release()
            raise self._failure

    def _job_done[T](self, future: Future[T]) -> None:
        # Record the failure before freeing the slot, so the caller that waits for the
        # slot sees it.
        if self._failure is None and not future.cancelled():
            self._failure = future.exception()
        self._slots.release()
