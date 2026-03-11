#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pty
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import IO

from omdlib.site_paths import SitePaths

from cmk.utils import tty


def call_scripts(
    site_name: str,
    phase: str,
    open_pty: bool,
    add_env: Mapping[str, str] | None = None,
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
        sys.stdout.write(f'Executing {phase} script "{file.name}"...')
        returncode = _call_script(open_pty, env, str(file))

        if not returncode:
            sys.stdout.write(tty.ok + "\n")
        else:
            sys.stdout.write(tty.error + " (exit code: %d)\n" % returncode)
            raise SystemExit(1)


def _call_script(  # pylint: disable=too-many-branches
    open_pty: bool, env: Mapping[str, str], command: str
) -> int:
    if open_pty:
        fd_parent, fd_child = pty.openpty()
        stdout = stderr = fd_child
    else:
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT

    with subprocess.Popen(  # nosec B602 # BNS:2b5952
        command,  # path-like args is not allowed when shell is true
        shell=True,
        stdout=stdout,
        stderr=stderr,
        encoding="utf-8",
        env=env,
    ) as proc:
        if open_pty:
            os.close(fd_child)
            parent: IO[str] = os.fdopen(fd_parent, buffering=1)
        else:
            assert proc.stdout is not None
            parent = proc.stdout

        wrote_output = False
        try:
            while True:
                line = parent.readline()
                if not line:
                    break
                if not wrote_output:
                    sys.stdout.write("\n")
                    wrote_output = True

                sys.stdout.write(f"-| {line}")
                sys.stdout.flush()
        except OSError:
            pass
        finally:
            if not pty:
                parent.close()
    return proc.returncode
