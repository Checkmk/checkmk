#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import enum
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from cmk import trace
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException

tracer = trace.get_tracer()


class CoreAction(enum.Enum):
    START = "start"
    RESTART = "restart"
    RELOAD = "reload"
    STOP = "stop"


class CoreClient(abc.ABC):
    # TODO: Replace the need for this by using polymorphism
    @classmethod
    @abc.abstractmethod
    def name(cls) -> Literal["nagios", "cmc"]: ...

    @abc.abstractmethod
    def cleanup_old_configs(self) -> None: ...

    @abc.abstractmethod
    def objects_file(self) -> Path: ...

    def run(self, action: CoreAction, log: Callable[[str], None]) -> None:
        with tracer.span(
            f"do_core_action[{action.value}]",
            attributes={
                __name__: self.name(),
            },
        ):
            log(f"Monitoring core: {action.value}")

            completed_process = self._run_command(action)
            if completed_process.returncode != 0:
                log(f"ERROR: {completed_process.stdout!r}\n")
                raise MKGeneralException(
                    f"Monitoring core: {action.value} failed: {completed_process.stdout!r}"
                )
            log(tty.ok + "\n")

    @abc.abstractmethod
    def _run_command(self, action: CoreAction) -> subprocess.CompletedProcess[bytes]: ...

    @abc.abstractmethod
    def _omd_name(self) -> str: ...

    def is_running(self) -> bool:
        return (
            subprocess.call(
                ["omd", "status", self._omd_name()],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            == 0
        )

    @abc.abstractmethod
    def config_is_valid(self, log1: Callable[[str], None], log2: Callable[[str], None]) -> bool: ...
