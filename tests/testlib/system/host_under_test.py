#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The machine a system test installs the agent on, and the only way to reach it.

Today that machine is the container pytest runs in. Cases that need kernel enforcement, or
Windows, will run against a virtual machine reached over SSH instead. A test that goes through
HostUnderTest keeps working when that happens. A test that calls subprocess directly does not.
"""

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Protocol

from tests.testlib.common.utils2 import run


class HostUnderTest(Protocol):
    def run(
        self, args: Sequence[str], *, sudo: bool = False, check: bool = True
    ) -> subprocess.CompletedProcess[str]: ...

    def copy_to(self, source: Path, target: PurePosixPath) -> None: ...

    def copy_from(self, source: PurePosixPath, target: Path) -> None: ...


class LocalHost:
    """The machine pytest runs on is the host under test."""

    def run(
        self, args: Sequence[str], *, sudo: bool = False, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return run(list(args), sudo=sudo, check=check)

    def copy_to(self, source: Path, target: PurePosixPath) -> None:
        self.run(["cp", source.as_posix(), target.as_posix()], sudo=True)

    def copy_from(self, source: PurePosixPath, target: Path) -> None:
        self.run(["cp", source.as_posix(), target.as_posix()], sudo=True)
        self.run(["chown", f"{os.getuid()}:{os.getgid()}", target.as_posix()], sudo=True)
