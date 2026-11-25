#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import os
import sys
from contextlib import suppress
from pathlib import Path

lock_path = Path(sys.stdin.readline().strip())

# Keep in sync with packages/cmk-backup/cmk/backup/mkbackup/__init__.py::exclusive_owner
lock_path.parent.mkdir(parents=True, exist_ok=True)
fd = os.open(lock_path, os.O_RDONLY | os.O_CREAT | os.O_CLOEXEC, 0o600)
try:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("Couldn't acquire lock")
    sys.stdout.write("locked\n")
    sys.stdout.flush()

    # We use the closing of stdin as a signal to shut down the process. An alternative would be
    # a standard signal, but the call site doesn't know our PID because we are called via
    # `sudo su ...`. Therefore, the call site only knows the the PID of the su process.
    sys.stdin.read()

finally:
    with suppress(OSError):
        os.close(fd)
