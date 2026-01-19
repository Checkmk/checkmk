#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Final, Literal

from cmk.ccc import tty
from cmk.ccc.config_path import cleanup_old_configs

from ._interface import CoreAction, CoreClient


class NagiosClient(CoreClient):
    def __init__(
        self,
        *,
        objects_file: Path,
        init_script: Path,
        config_file: Path,
        binary_file: Path,
        cleanup_base: Path,
    ) -> None:
        super().__init__()
        self._objects_file: Final = objects_file
        self.init_script: Final = init_script
        self.config_file: Final = config_file
        self.binary: Final = binary_file
        self.cleanup_base: Final = cleanup_base

    def cleanup_old_configs(self) -> None:
        cleanup_old_configs(self.cleanup_base)

    def objects_file(self) -> Path:
        return self._objects_file

    def _run_command(self, action: CoreAction) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            # We can't _easily_ use omd here, because it will eat our CORE_NOVERIFY environment variable.
            # TODO: fix omd in that regard
            [str(self.init_script), action.value],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            check=False,
            env={**os.environ, "CORE_NOVERIFY": "yes"},
        )

    def _omd_name(self) -> Literal["nagios"]:
        return "nagios"

    def config_is_valid(
        self, log_stdout: Callable[[str], None], log_verbose: Callable[[str], None]
    ) -> bool:
        if not self.config_file.exists():
            return True

        command = [str(self.binary), "-vp", str(self.config_file)]
        log_verbose(f"Running '{subprocess.list2cmdline(command)}'")
        log_stdout("Validating Nagios configuration...")

        completed_process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            encoding="utf-8",
            check=False,
        )
        if not completed_process.returncode:
            log_stdout(tty.ok + "\n")
            return True

        log_stdout(f"ERROR:\n{completed_process.stdout}")
        return False
