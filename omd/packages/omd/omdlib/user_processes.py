#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import os
import signal
import subprocess
import sys
import time

import psutil

from omdlib.console import ok


def terminate_site_user_processes(username: str, verbose: bool) -> None:
    """Sends a SIGTERM to all running site processes and waits up to 5 seconds for termination

    In case one or more processes are still running after the timeout, the method will make
    the current OMD call terminate.
    """

    pids = _site_user_processes(username, exclude_current_and_parents=True)
    if not pids:
        return

    sys.stdout.write("Stopping %d remaining site processes..." % len(pids))

    timeout_at = time.time() + 5
    sent_terminate = False
    while pids and time.time() < timeout_at:
        for pid in pids[:]:
            try:
                if not sent_terminate:
                    if verbose:
                        sys.stdout.write("%d..." % pid)
                    os.kill(pid, signal.SIGTERM)
                else:
                    os.kill(pid, signal.SIG_DFL)
            except OSError as e:
                if e.errno == errno.ESRCH:  # No such process
                    pids.remove(pid)
                else:
                    raise

        sent_terminate = True
        time.sleep(0.1)

    if pids:
        sys.exit("\nFailed to stop remaining site processes: %s" % ", ".join(map(str, pids)))
    else:
        ok()


def kill_site_user_processes(
    username: str,
    verbose: bool,
    exclude_current_and_parents: bool = False,
) -> None:
    pids = _site_user_processes(username, exclude_current_and_parents)
    tries = 5
    while tries > 0 and pids:
        for pid in pids[:]:
            try:
                if verbose:
                    sys.stdout.write("Killing process %d..." % pid)
                os.kill(pid, signal.SIGKILL)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    pids.remove(pid)  # No such process
                else:
                    raise
        time.sleep(1)
        tries -= 1

    if pids:
        sys.exit("Failed to kill site processes: %s" % ", ".join(map(str, pids)))


def _get_current_and_parent_pids() -> list[int]:
    """Return list of PIDs of the current process and parent process tree till pid 0"""
    pids = []
    process = psutil.Process()
    while process and process.pid != 0:
        pids.append(process.pid)
        process = process.parent()
    return pids


def _site_user_processes(username: str, exclude_current_and_parents: bool) -> list[int]:
    """Return list of PIDs of all running site user processes (that are not excluded)"""
    exclude: list[int] = []
    if exclude_current_and_parents:
        exclude = _get_current_and_parent_pids()
    with subprocess.Popen(
        ["ps", "-U", username, "-o", "pid", "--no-headers"],
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ) as user_process:
        exclude.append(user_process.pid)
        pids = []
        for l in user_process.communicate()[0].split("\n"):
            line = l.strip()
            if not line:
                continue
            pid = int(line)
            if pid in exclude:
                continue
            pids.append(pid)
    return pids
