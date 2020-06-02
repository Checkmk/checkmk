#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import signal
import subprocess
from types import TracebackType
from typing import Optional, Type, Union

from six import ensure_binary, ensure_str

from cmk.utils.exceptions import MKTimeout
from cmk.utils.type_defs import RawAgentData

from ._base import AbstractDataFetcher, MKFetcherError


class ProgramDataFetcher(AbstractDataFetcher):
    def __init__(
            self,
            cmdline,  # type: Union[bytes, str]
            stdin,  # type: Optional[str]
            is_cmc,  # type: bool
    ):
        # type: (...) -> None
        super(ProgramDataFetcher, self).__init__()
        self._cmdline = cmdline
        self._stdin = stdin
        self._is_cmc = is_cmc
        self._logger = logging.getLogger("cmk.fetchers.program")
        self._process = None  # type: Optional[subprocess.Popen]

    def __enter__(self):
        # type: () -> ProgramDataFetcher
        if self._is_cmc:
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
                self._cmdline,
                shell=True,
                stdin=subprocess.PIPE if self._stdin else open(os.devnull),
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
                self._cmdline,
                shell=True,
                stdin=subprocess.PIPE if self._stdin else open(os.devnull),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        if self._process is None:
            return
        if exc_type is MKTimeout:
            # On timeout exception try to stop the process to prevent child process "leakage"
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

    def data(self):
        # type: () -> RawAgentData
        if self._process is None:
            raise MKFetcherError("No process")
        stdout, stderr = self._process.communicate(
            input=ensure_binary(self._stdin) if self._stdin else None)
        if self._process.returncode == 127:
            exepath = self._cmdline.split()[0]  # for error message, hide options!
            raise MKFetcherError("Program '%s' not found (exit code 127)" % ensure_str(exepath))
        if self._process.returncode:
            raise MKFetcherError("Agent exited with code %d: %s" %
                                 (self._process.returncode, ensure_str(stderr)))
        return stdout
