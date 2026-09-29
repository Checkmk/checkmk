#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Reads the agent's output from its TCP port, for the regression and integration suites.

Like the Checkmk server in legacy pull mode, it connects, sends nothing and reads until
the agent closes the connection. Every way this can go wrong fails the test with its own
error: before, a bug in the reader or in the retries looked like an agent that sent
nothing.
"""

import socket
import time


def _read_once(host: str, port: int, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    chunks: list[bytes] = []
    with socket.create_connection((host, port), timeout=timeout) as conn:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"agent output not complete after {timeout} s")
            conn.settimeout(remaining)
            if not (chunk := conn.recv(65536)):
                break
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


def read_agent_output(
    host: str,
    port: int,
    tries: int = 5,
    delay: float = 2.0,
    timeout: float = 120.0,
    empty_ok: bool = False,
) -> str:
    """The agent's output, trying again while it is not listening or sends nothing yet.

    An overloaded machine may delay the start of the agent process. Only connection
    errors (refused, reset: OSError) and empty output are retried; any other
    exception fails the test with its own traceback. A try that is not over after
    timeout seconds fails at once: the agent is running but hangs, and trying again
    would only wait again. The default timeout leaves room for the 60 s plugin
    timeouts some regression tests configure. Empty output after the last try fails
    too, unless the caller expects the output may be empty (empty_ok). A last try
    that failed to connect always fails, naming its error: an agent that is not
    running has not sent empty output.
    """
    error: Exception | None = None
    tried = 0
    for attempt in range(tries):
        if attempt:
            time.sleep(delay)
        tried += 1
        try:
            output = _read_once(host, port, timeout)
        except TimeoutError as e:
            error = e
            break
        except OSError as e:
            output, error = "", e
        else:
            error = None
        if output:
            return output
    message = f"no agent output from {host}:{port} after {tried} {'try' if tried == 1 else 'tries'}"
    if error is not None:
        raise AssertionError(f"{message}, the last one failed: {error!r}") from error
    if empty_ok:
        return ""
    raise AssertionError(message)
