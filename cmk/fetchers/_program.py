#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import signal
import subprocess
from contextlib import suppress
from typing import Final

from cmk.ccc.exceptions import MKFetcherError

from cmk.utils.agentdatatype import AgentRawData

from ._abstract import Fetcher, Mode


class ProgramFetcher(Fetcher[AgentRawData]):
    def __init__(
        self,
        *,
        cmdline: str,
        stdin: str | None,
        is_cmc: bool,
    ) -> None:
        super().__init__()
        self.cmdline: Final = cmdline
        self.stdin: Final = stdin
        self.is_cmc: Final = is_cmc
        self._logger: Final = logging.getLogger("cmk.helper.program")
        self._process: subprocess.Popen | None = None

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"cmdline={self.cmdline!r}",
                    f"stdin={self.stdin!r}",
                    f"is_cmc={self.is_cmc!r}",
                )
            )
            + ")"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProgramFetcher):
            return False
        return (
            self.cmdline == other.cmdline
            and self.stdin == other.stdin
            and self.is_cmc == other.is_cmc
        )

    def open(self) -> None:
        self._logger.debug("Calling: %s", self.cmdline)
        if self.stdin:
            self._logger.debug(
                "STDIN (first 30 bytes): %s... (total %d bytes)",
                self.stdin[:30],
                len(self.stdin),
            )

        # We can not create a separate process group when running Nagios
        # Upon reaching the service_check_timeout Nagios only kills the process
        # group of the active check.
        start_new_session = self.is_cmc

        self._process = subprocess.Popen(  # nosec 602 # BNS:b00359
            self.cmdline,
            shell=True,
            stdin=subprocess.PIPE if self.stdin else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=start_new_session,
            close_fds=True,
        )

    def close(self):
        if self._process is None:
            return

        # Try to kill the process to prevent process "leakage".
        #
        # Please note that we have two different situations here:
        #
        # CMC: self._process is in a dedicated process group. By killing the process group we
        # can terminate self._process and all it's child processes.
        #
        # Nagios: self._process is in the same process group as we are (See comment of
        # subprocess.Popen) for the reason). In this situation killing the process group would
        # also kill our own process. This must not be done.
        if self.is_cmc:
            with suppress(OSError):
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                self._process.wait()

        # The stdout and stderr pipe are not closed correctly on a MKTimeout
        # Normally these pipes getting closed after p.communicate finishes
        # Closing them a second time in a OK scenario won't hurt neither..
        if self._process.stdout is None or self._process.stderr is None:
            raise Exception("stdout needs to be set")

        self._process.stdout.close()
        self._process.stderr.close()
        self._process = None

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        self._logger.debug("Get data from program")
        if self._process is None:
            raise TypeError("no process")
        # ? do they have the default byte type, because in open() none of the "text", "encoding",
        #  "errors", "universal_newlines" were specified?
        stdout, stderr = self._process.communicate(
            input=self.stdin.encode() if self.stdin else None
        )
        if self._process.returncode == 127:
            exepath = self.cmdline.split()[0]  # for error message, hide options!
            raise MKFetcherError(f"Program '{exepath}' not found (exit code 127)")
        if self._process.returncode:
            raise MKFetcherError(
                f"Agent exited with code {self._process.returncode}: {stderr.decode().strip()}"
            )
        return stdout
