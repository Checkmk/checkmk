#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import os
import signal
import sys
import time
from collections.abc import Generator, Iterable
from contextlib import suppress

import psutil

from omdlib.console import ok


def terminate_site_user_processes(username: str, verbose: bool) -> None:
    """Sends a SIGTERM to all running site processes and waits up to 5 seconds for termination

    In case one or more processes are still running after the timeout, the method will make
    the current OMD call terminate.
    """

    processes = _site_user_processes(username)
    if not processes:
        return

    sys.stdout.write("Stopping %d remaining site processes..." % len(processes))

    timeout_at = time.time() + 5
    sent_terminate = False
    while processes and time.time() < timeout_at:
        for process in processes[:]:
            try:
                if not sent_terminate:
                    if verbose:
                        sys.stdout.write("%d..." % process.pid)
                    os.kill(process.pid, signal.SIGTERM)
                else:
                    os.kill(process.pid, signal.SIG_DFL)
            except OSError as e:
                if e.errno == errno.ESRCH:  # No such process
                    processes.remove(process)
                else:
                    raise

        sent_terminate = True
        time.sleep(0.1)

    if remaining_processes_descriptions := list(_descriptions_of_remaining_processes(processes)):
        sys.exit(
            "\n".join(
                [
                    "\nFailed to stop remaining site processes:",
                    *remaining_processes_descriptions,
                ]
            )
        )
    else:
        ok()


def kill_site_user_processes(username: str, verbose: bool) -> None:
    processes = _site_user_processes(username)
    tries = 5
    while tries > 0 and processes:
        for process in processes[:]:
            try:
                if verbose:
                    sys.stdout.write(f"Killing process {process.pid}...")
                os.kill(process.pid, signal.SIGKILL)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    processes.remove(process)  # No such process
                else:
                    raise
        time.sleep(1)
        tries -= 1

    if remaining_processes_descriptions := list(_descriptions_of_remaining_processes(processes)):
        sys.exit(
            "\n".join(
                [
                    "\nFailed to kill site processes:",
                    *remaining_processes_descriptions,
                ]
            )
        )


def _descriptions_of_remaining_processes(
    remaining_processes: Iterable[psutil.Process],
) -> Generator[str]:
    for process in remaining_processes:
        with suppress(psutil.NoSuchProcess):
            yield f"{process.pid}, command line: `{' '.join(process.cmdline()).strip()}`, status: {process.status()}"


def _get_current_and_parent_processes() -> list[psutil.Process]:
    """Return list of the current process and parent process tree till pid 0"""
    processes = []
    process: psutil.Process | None = psutil.Process()
    while process and process.pid != 0:
        processes.append(process)
        process = process.parent()
    return processes


def _site_user_processes(username: str) -> list[psutil.Process]:
    """Return list of all running site user processes (that are not excluded)"""
    exclude = set(_get_current_and_parent_processes())
    processes_of_site_user = set()
    for process in psutil.process_iter():
        try:
            process_owner = process.username()
        except psutil.NoSuchProcess:
            continue
        if process_owner == username:
            processes_of_site_user.add(process)
    return list(processes_of_site_user - exclude)
