#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import threading
from collections.abc import Iterator
from multiprocessing.pool import ThreadPool

import flask
import pytest
from flask.globals import request

from cmk.gui.config import active_config
from cmk.gui.utils.request_context import copy_request_context


def _run_in_thread(attr: str) -> tuple[bool, str]:
    return getattr(active_config, attr), request.url


def test_thread_pool_request_context(flask_app: flask.Flask) -> None:
    path = "/NO_SITE/check_mk/index.html"
    with flask_app.test_request_context(path):
        flask_app.preprocess_request()

        size = 10
        jobs = ["debug"] * (size * 100)
        with ThreadPool(size) as pool:
            results = pool.map(
                copy_request_context(_run_in_thread),
                jobs,
            )

    assert len(results) == len(jobs)
    for debug, url in results:
        assert not debug
        assert url.endswith(path)


@contextlib.contextmanager
def reraise_exceptions_from_threads() -> Iterator[None]:
    """Reraise an exception from a thread which is started in this context.

    Acts like a context manager, and you use it like that.

    Examples:
        This will reraise the exception from the thread in the main thread.

        with reraise_exceptions_from_threads():
             thread_which_crashes = Thread(target=crash)
             thread_which_crashes.start()

    Returns:
        The context manager.

    """
    exc_hook_calls: list[threading.ExceptHookArgs] = []

    def remember_exceptions(exc: threading.ExceptHookArgs) -> None:
        exc_hook_calls.append(exc)

    prev = threading.excepthook
    threading.excepthook = remember_exceptions

    try:
        yield
    finally:
        # Restore the previous one installed. In our case for sure the one from pytest.
        threading.excepthook = prev

    if exc_hook_calls:
        # Unhandled exceptions will bring the thread to a close, so we can assume to only have one.
        exc_call = exc_hook_calls[0]
        raise exc_call.exc_type(exc_call.exc_value).with_traceback(exc_call.exc_traceback)


def test_threading_error_message(flask_app: flask.Flask) -> None:
    path = "/NO_SITE/check_mk/index.html"
    with flask_app.test_request_context(path):
        flask_app.preprocess_request()

        # We run in another thread WITHOUT copying over the request context.
        with (
            pytest.raises(RuntimeError, match="copy_request_context"),
            reraise_exceptions_from_threads(),
        ):
            thread = threading.Thread(name="test", target=_run_in_thread, args=("debug",))
            thread.start()
            thread.join()
