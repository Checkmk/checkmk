#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Run a command and print output only after a given amount of time in seconds

E.g. `decent-output 2 docker build .`
"""

import signal
import sys
from asyncio import create_subprocess_exec, gather, Queue, run, StreamReader, wait_for
from asyncio import TimeoutError as AsyncTimeoutError
from asyncio.subprocess import PIPE, Process
from collections.abc import Sequence
from contextlib import suppress
from typing import TextIO

LineQueue = Queue[None | tuple[TextIO, bytes]]


async def print_after(
    timeout: float,
    abort: Queue[bool],
    buffer: LineQueue,
) -> None:
    """Wait for a given time or until aborted - print buffer contents if appropriate"""
    with suppress(AsyncTimeoutError):
        if await wait_for(abort.get(), timeout):
            return
    while elem := await buffer.get():
        out_file, line = elem
        out_file.write(line.decode(errors="replace"))


async def buffer_stream(stream: StreamReader, buffer: LineQueue, out_file: TextIO) -> None:
    """Records a given stream to a buffer line by line along with the source"""
    while line := await stream.readline():
        await buffer.put((out_file, line))
    await buffer.put(None)


async def wait_and_notify(process: Process, abort: Queue[bool]) -> None:
    """Just waits for @process to finish and notify the result"""
    await process.wait()
    await abort.put(process.returncode == 0)


async def run_quiet_and_verbose(timeout: float, cmd: Sequence[str]) -> int:
    """Run a command and start printing it's output only after a given timeout"""
    buffer: LineQueue = Queue()
    abort: Queue[bool] = Queue()

    process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)

    assert process.stdout and process.stderr

    signal.signal(signal.SIGINT, lambda _sig, _frame: 0)

    await gather(
        print_after(float(timeout), abort, buffer),
        buffer_stream(process.stdout, buffer, sys.stdout),
        buffer_stream(process.stderr, buffer, sys.stderr),
        wait_and_notify(process, abort),
    )
    raise SystemExit(process.returncode)


def main() -> None:
    """Just the entrypoint for run_quiet_and_verbose()"""
    timeout, *cmd = sys.argv[1:]
    run(run_quiet_and_verbose(float(timeout), cmd))


if __name__ == "__main__":
    main()
