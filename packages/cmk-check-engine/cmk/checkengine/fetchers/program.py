#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import logging
import os
import signal
import subprocess
from contextlib import suppress
from typing import Final, override, Self, TypedDict

from cmk.checkengine.fetcher_abc import DeserializationContext, Fetcher, FetcherError, Mode
from cmk.checkengine.helper_interface import AgentRawData

logger = logging.getLogger(__name__)


class ProgramFetcherParams(TypedDict):
    cmdline: str
    stdin: str | None
    is_cmc: bool


class ProgramFetcher(Fetcher[AgentRawData, ProgramFetcherParams]):
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
        self._process: subprocess.Popen | None = None

    @override
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

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProgramFetcher):
            return False
        return (
            self.cmdline == other.cmdline
            and self.stdin == other.stdin
            and self.is_cmc == other.is_cmc
        )

    @override
    def serialized_params(self) -> ProgramFetcherParams:
        return {"cmdline": self.cmdline, "stdin": self.stdin, "is_cmc": self.is_cmc}

    @classmethod
    @override
    def from_params(cls, params: ProgramFetcherParams, _ctx: DeserializationContext) -> Self:
        return cls(**params)

    @override
    def open(self) -> None:
        logger.debug("Calling: %(cmdline)s", {"cmdline": self.cmdline})
        if self.stdin:
            logger.debug(
                "STDIN (first 30 bytes): %(stdin_head)s... (total %(stdin_len)d bytes)",
                {"stdin_head": self.stdin[:30], "stdin_len": len(self.stdin)},
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

    @override
    def close(self) -> None:
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

    @override
    def _fetch_from_io(self, _mode: Mode) -> AgentRawData:
        logger.debug("Get data from program")
        if self._process is None:
            raise TypeError("no process")
        # ? do they have the default byte type, because in open() none of the "text", "encoding",
        #  "errors", "universal_newlines" were specified?
        stdout, stderr = self._process.communicate(
            input=self.stdin.encode() if self.stdin else None
        )
        if self._process.returncode:
            logger.error(
                "Program fetcher failure. Command: '%(cmdline)s'. Exit code: %(exit_code)s. "
                "Error message: %(error)s",
                {
                    "cmdline": self.cmdline,
                    "exit_code": self._process.returncode,
                    "error": stderr.decode() if hasattr(stderr, "decode") else stderr,
                },
            )
            # FYI: We do not want to expose any details about the command in the UI.
            # It might contain sensitive information!
            raise FetcherError(
                f"Program exited with status {self._process.returncode}. See log for details."
            )
        return stdout
