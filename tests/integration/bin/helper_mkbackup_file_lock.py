#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import os
import sys
from pathlib import Path

lock_path = Path(sys.stdin.readline().strip())
lock_file_descriptor: int | None = None

try:
    lock_file_descriptor = os.open(
        lock_path,
        os.O_RDONLY | os.O_CREAT,
        mode=0o660,
    )
    fcntl.flock(lock_file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    sys.stdout.write("locked\n")
    sys.stdout.flush()

    # We use the closing of stdin as a signal to shut down the process. An alternative would be
    # a standard signal, but the call site doesn't know our PID because we are called via
    # `sudo su ...`. Therefore, the call site only knows the the PID of the su process.
    sys.stdin.read()


finally:
    if lock_file_descriptor is not None:
        os.close(lock_file_descriptor)
