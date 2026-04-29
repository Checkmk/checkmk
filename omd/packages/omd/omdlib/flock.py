#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path


@contextmanager
def exclusive_owner(path: Path, message: str) -> Iterator[None]:
    """Ensure that this process is unique per site (analogous to a PID file lock).

    Child processes will inherit this lock unless explicitly dropped.

    This implementation is deliberately minimal. It foregoes handling edge cases (e.g., io_uring
    lingering, orphaned inodes after unlinking, or symlink TOCTOU attacks) in favor of the
    following strict assumptions:

    * `path` must be in a dedicated directory protected by access permissions (e.g., `/run` or
      `/var/lock`). Do not use shared sticky-bit directories like `/tmp`.
    * `path` must reside on a local filesystem. `flock` semantics are unreliable on network mounts
      (NFS) and FAT. In practice this is not a concern: Linux has supported advisory NFS locks via
      lockd/NLM since 2.6.12 (2005), and FAT does not support symlinks, making it unsuitable for
      hosting a Checkmk site regardless. `flock` is used elsewhere already (e.g. CMC and
      `cmk.ccc.store`).
    * `path` must never be deleted while the process is running, as `flock` locks the underlying
       inode, not the path.
    * `flock` is per-process, not per-thread. It does not prevent race conditions between threads.

    For locking implementations that securely handles these edge cases, see:
    * TigerBeetle: https://github.com/tigerbeetle/tigerbeetle/blob/f051a0b0e15c77b292a4ca1e9409db41e35703e1/src/io/linux.zig#L1609-L1652
    * Systemd: https://github.com/systemd/systemd/blob/37c272228dbdbcb4f60609d273d1352ccac061b7/src/tmpfiles/tmpfiles.c#L761
    * Filelock: https://github.com/tox-dev/filelock/blob/eb526ec4edfd91aef607b54bf77a467f04b8f897/src/filelock/_unix.py#L33-L111
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(message)
        yield
    finally:
        with suppress(OSError):
            os.close(fd)
