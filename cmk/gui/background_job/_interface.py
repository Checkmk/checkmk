#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import time
from logging import Logger
from pathlib import Path
from typing import Callable, NamedTuple

from cmk.utils import render

from ._defines import BackgroundJobDefines


class BackgroundProcessInterface:
    def __init__(self, work_dir: str, job_id: str, logger: Logger) -> None:
        self._work_dir = work_dir
        self._job_id = job_id
        self._logger = logger

    def get_work_dir(self) -> str:
        return self._work_dir

    def get_job_id(self) -> str:
        return self._job_id

    def get_logger(self) -> Logger:
        return self._logger

    def send_progress_update(self, info: str, with_timestamp: bool = False) -> None:
        """The progress update is written to stdout and will be caught by the threads counterpart"""
        message = info
        if with_timestamp:
            message = f"{render.time_of_day(time.time())} {message}"
        sys.stdout.write(message + "\n")

    def send_result_message(self, info: str) -> None:
        """The result message is written to a distinct file to separate this info from the rest of
        the context information. This message should contain a short result message and/or some kind
        of resulting data, e.g. a link to a report or an agent output. As it may contain HTML code
        it is not written to stdout."""
        encoded_info = "%s\n" % info
        result_message_path = (
            Path(self.get_work_dir()) / BackgroundJobDefines.result_message_filename
        )
        with result_message_path.open("ab") as f:
            f.write(encoded_info.encode())

    def send_exception(self, info: str) -> None:
        """Exceptions are written to stdout because of log output clarity
        as well as into a distinct file, to separate this info from the rest of the context information
        """
        # Exceptions also get an extra newline, since some error messages tend not output a \n at the end..
        encoded_info = "%s\n" % info
        sys.stdout.write(encoded_info)
        with (Path(self.get_work_dir()) / BackgroundJobDefines.exceptions_filename).open("ab") as f:
            f.write(encoded_info.encode())


class JobParameters(NamedTuple):
    """Just a small wrapper to help improve the typing through multiprocessing.Process call"""

    work_dir: str
    job_id: str
    target: Callable[[BackgroundProcessInterface], None]
    lock_wato: bool
    is_stoppable: bool
    override_job_log_level: int | None
