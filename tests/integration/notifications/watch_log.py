#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import os
import subprocess
import sys
import time

from psutil import Process

from tests.testlib.site import Site


class WatchLog:
    """Small helper for integration tests: Watch a sites log file"""

    def __init__(self, site: Site, default_timeout: int | None = None) -> None:
        self._site = site
        self._log_path = site.core_history_log()
        self._default_timeout = default_timeout or site.core_history_log_timeout()

        self._tail_process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "WatchLog":
        if not self._site.file_exists(self._log_path):
            self._site.write_file(self._log_path, "")

        self._tail_process = self._site.execute(
            ["tail", "-f", self._log_path.as_posix()],
            stdout=subprocess.PIPE,
            bufsize=1,  # line buffered
        )

        # Make stdout non blocking. Otherwise the timeout handling
        # in _check_for_line will not work
        assert self._tail_process.stdout is not None
        fd = self._tail_process.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._tail_process is not None:
            for c in Process(self._tail_process.pid).children(recursive=True):
                if c.name() == "tail":
                    assert self._site.execute(["kill", str(c.pid)]).wait() == 0
            self._tail_process.wait()
            self._tail_process = None

    def check_logged(self, match_for: str, timeout: float | None = None) -> None:
        if timeout is None:
            timeout = self._default_timeout
        found, lines = self._check_for_line(match_for, timeout)
        if not found:
            raise Exception(
                "Did not find %r in %s after %d seconds\n'%s'"
                % (match_for, self._log_path, timeout, lines)
            )

    def check_not_logged(self, match_for: str, timeout: float | None = None) -> None:
        if timeout is None:
            timeout = self._default_timeout
        found, lines = self._check_for_line(match_for, timeout)
        if found:
            raise Exception(
                "Found %r in %s after %d seconds\n'%s'"
                % (match_for, self._log_path, timeout, lines)
            )

    def _check_for_line(self, match_for: str, timeout: float) -> tuple[bool, str]:
        if self._tail_process is None:
            raise Exception("no log file")
        timeout_at = time.time() + timeout
        sys.stdout.write(
            "Start checking for matching line %r at %d until %d\n"
            % (match_for, time.time(), timeout_at)
        )
        lines: list[str] = []
        while time.time() < timeout_at:
            # print("read till timeout %0.2f sec left" % (timeout_at - time.time()))
            assert self._tail_process.stdout is not None
            line = self._tail_process.stdout.readline()
            lines += line
            if line:
                sys.stdout.write("PROCESS LINE: %r\n" % line)
            if match_for in line:
                return True, "".join(lines)
            time.sleep(0.1)

        sys.stdout.write("Timed out at %d\n" % (time.time()))
        return False, "".join(lines)
