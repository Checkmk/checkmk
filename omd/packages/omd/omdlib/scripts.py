#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import contextlib
import os
import pty
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import IO

from omdlib.site_paths import SitePaths

from cmk.ccc import tty


def call_scripts(
    site_name: str, phase: str, open_pty: bool, add_env: Mapping[str, str] | None = None
) -> None:
    """Calls hook scripts in defined directories."""
    site_home = SitePaths.from_site_name(site_name).home
    path = Path(site_home, "lib", "omd", "scripts", phase)
    if not path.exists():
        return

    env = {
        **os.environ,
        "OMD_ROOT": site_home,
        "OMD_SITE": site_name,
        **(add_env if add_env else {}),
    }

    # NOTE: scripts have an order!
    for file in sorted(path.iterdir()):
        if file.name[0] == ".":
            continue
        if not file.is_file():
            continue
        sys.stdout.write(f'Executing {phase} script "{file.name}"...')
        returncode = _call_script(open_pty, env, [str(file)])

        if not returncode:
            sys.stdout.write(tty.ok + "\n")
        else:
            sys.stdout.write(tty.error + " (exit code: %d)\n" % returncode)
            raise SystemExit(1)


def _call_script(
    open_pty: bool,
    env: Mapping[str, str],
    command: Sequence[str],
) -> int:
    def forward_to_stdout(text_io: IO[str]) -> None:
        line = text_io.readline()
        if line:
            sys.stdout.write("\n")
            sys.stdout.write(f"-| {line}")
            for line in text_io:
                sys.stdout.write(f"-| {line}")

    if open_pty:
        fd_parent, fd_child = pty.openpty()
        with subprocess.Popen(
            command,
            stdout=fd_child,
            stderr=fd_child,
            encoding="utf-8",
            env=env,
        ) as proc:
            os.close(fd_child)
            with open(fd_parent) as parent:
                with contextlib.suppress(OSError):
                    forward_to_stdout(parent)
    else:
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            env=env,
        ) as proc:
            assert proc.stdout is not None
            forward_to_stdout(proc.stdout)
    return proc.returncode
