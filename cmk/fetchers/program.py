#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import signal
import subprocess
from contextlib import suppress
from typing import Any, Dict, Final, Optional, Union

from six import ensure_binary, ensure_str

from cmk.utils.type_defs import AgentRawData

from . import MKFetcherError
from .agent import AgentFetcher, DefaultAgentFileCache
from .type_defs import Mode


class ProgramFetcher(AgentFetcher):
    def __init__(
        self,
        file_cache: DefaultAgentFileCache,
        *,
        cmdline: Union[bytes, str],
        stdin: Optional[str],
        is_cmc: bool,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.fetchers.program"))
        self.cmdline: Final = cmdline
        self.stdin: Final = stdin
        self.is_cmc: Final = is_cmc
        self._process: Optional[subprocess.Popen] = None

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "ProgramFetcher":
        return cls(
            DefaultAgentFileCache.from_json(serialized.pop("file_cache")),
            **serialized,
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "cmdline": self.cmdline,
            "stdin": self.stdin,
            "is_cmc": self.is_cmc,
        }

    def open(self) -> None:
        self._logger.debug("Calling: %s", self.cmdline)
        if self.stdin:
            self._logger.debug(
                "STDIN (first 30 bytes): %s... (total %d bytes)",
                self.stdin[:30],
                len(self.stdin),
            )

        if self.is_cmc:
            # Warning:
            # The preexec_fn parameter is not safe to use in the presence of threads in your
            # application. The child process could deadlock before exec is called. If you
            # must use it, keep it trivial! Minimize the number of libraries you call into.
            #
            # Note:
            # If you need to modify the environment for the child use the env parameter
            # rather than doing it in a preexec_fn. The start_new_session parameter can take
            # the place of a previously common use of preexec_fn to call os.setsid() in the
            # child.
            self._process = subprocess.Popen(  # nosec
                self.cmdline,
                shell=True,
                stdin=subprocess.PIPE if self.stdin else open(os.devnull),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                close_fds=True,
            )
        else:
            # We can not create a separate process group when running Nagios
            # Upon reaching the service_check_timeout Nagios only kills the process
            # group of the active check.
            self._process = subprocess.Popen(  # nosec
                self.cmdline,
                shell=True,
                stdin=subprocess.PIPE if self.stdin else open(os.devnull),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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

    def _is_cache_enabled(self, mode: Mode) -> bool:
        return mode is not Mode.CHECKING

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        if self._process is None:
            raise MKFetcherError("No process")
        stdout, stderr = self._process.communicate(
            input=ensure_binary(self.stdin) if self.stdin else None)
        if self._process.returncode == 127:
            exepath = self.cmdline.split()[0]  # for error message, hide options!
            raise MKFetcherError("Program '%s' not found (exit code 127)" % ensure_str(exepath))
        if self._process.returncode:
            raise MKFetcherError("Agent exited with code %d: %s" %
                                 (self._process.returncode, ensure_str(stderr)))
        return stdout
