#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
from pathlib import Path
from typing import Final, Literal

from cmk.ccc.config_path import cleanup_old_configs

from ._interface import CoreAction, CoreClient


class NagiosClient(CoreClient):
    def __init__(
        self,
        *,
        objects_file: Path,
        init_script: Path,
        cleanup_base: Path,
    ) -> None:
        super().__init__()
        self._objects_file: Final = objects_file
        self.init_script: Final = init_script
        self.cleanup_base: Final = cleanup_base

    @classmethod
    def name(cls) -> Literal["nagios"]:
        return "nagios"

    def cleanup_old_configs(self) -> None:
        cleanup_old_configs(self.cleanup_base)

    def objects_file(self) -> Path:
        return self._objects_file

    def _run_command(self, action: CoreAction) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            # can we use omd here as well? Will CORE_NOVERIFY survive?
            [str(self.init_script), action.value],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            check=False,
            env={**os.environ, "CORE_NOVERIFY": "yes"},
        )

    def _omd_name(self) -> Literal["nagios"]:
        return "nagios"
