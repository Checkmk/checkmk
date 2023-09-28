#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module cares about Check_MK's file storage accessing. Most important
functionality is the locked file opening realized with the File() context
manager."""

import errno
import fcntl
import logging
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import cmk.utils.paths
from cmk.utils.exceptions import MKConfigLockTimeout, MKTimeout
from cmk.utils.i18n import _

_all = [
    "acquire_lock",
    "cleanup_locks",
    "configuration_lockfile",
    "have_lock",
    "lock_checkmk_configuration",
    "lock_exclusive",
    "locked",
    "release_all_locks",
    "release_lock",
    "try_acquire_lock",
    "try_locked",
]

logger = logging.getLogger("cmk.store")

#   .--Predefined----------------------------------------------------------.
#   |          ____               _       __ _                _            |
#   |         |  _ \ _ __ ___  __| | ___ / _(_)_ __   ___  __| |           |
#   |         | |_) | '__/ _ \/ _` |/ _ \ |_| | '_ \ / _ \/ _` |           |
#   |         |  __/| | |  __/ (_| |  __/  _| | | | |  __/ (_| |           |
#   |         |_|   |_|  \___|\__,_|\___|_| |_|_| |_|\___|\__,_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Predefined locks                                                     |
#   '----------------------------------------------------------------------'


def configuration_lockfile() -> str:
    # for our path monkeypatching to have an effect when executing the unit tests, we need to use
    # the full module path :(
    return cmk.utils.paths.default_config_dir + "/multisite.mk"


@contextmanager
def lock_checkmk_configuration() -> Iterator[None]:
    path = configuration_lockfile()
    try:
        acquire_lock(path)
    except MKTimeout as e:
        raise MKConfigLockTimeout(
            _(
                "Couldn't lock the Checkmk configuration. Another "
                "process is running that holds this lock. In order for you to be "
                "able to perform the desired action, you have to wait until the "
                "other process has finished. Please try again later."
            )
        ) from e

    try:
        yield
    finally:
        release_lock(path)


# TODO: Use lock_checkmk_configuration() and nuke this!
def lock_exclusive() -> None:
    acquire_lock(configuration_lockfile())


# .
#   .--File locking--------------------------------------------------------.
#   |          _____ _ _        _            _    _                        |
#   |         |  ___(_) | ___  | | ___   ___| | _(_)_ __   __ _            |
#   |         | |_  | | |/ _ \ | |/ _ \ / __| |/ / | '_ \ / _` |           |
#   |         |  _| | | |  __/ | | (_) | (__|   <| | | | | (_| |           |
#   |         |_|   |_|_|\___| |_|\___/ \___|_|\_\_|_| |_|\__, |           |
#   |                                                     |___/            |
#   +----------------------------------------------------------------------+
#   | Helper functions to lock files (between processes) for disk IO       |
#   | Currently only exclusive locks are implemented and they always will  |
#   | wait forever.                                                        |
#   '----------------------------------------------------------------------'

LockDict = dict[str, int]

# This will hold our path to file descriptor dicts in acquired_locks: dict[str, int].
_locks = threading.local()


def _acquired_locks() -> dict[str, int]:
    """Make access to global locking dict thread-safe.

    Only the thread which acquired the lock should see the file descriptor in the locking
    dictionary. In order to do this, the locking dictionary(*) is now an attribute on a
    threading.local() object, which has to be created at runtime. This decorator handles
    the creation of these dicts.

    (*) The dict is a mapping from path-name to file descriptor.
    """
    if not hasattr(_locks, "acquired_locks"):
        _locks.acquired_locks = {}
    acquired_locks: dict[str, int] = _locks.acquired_locks
    return acquired_locks


def _set_lock(name: str, fd: int) -> None:
    _acquired_locks()[name] = fd


def _get_lock(name: str) -> int | None:
    return _acquired_locks().get(name)


def _del_lock(name: str) -> None:
    _acquired_locks().pop(name, None)


def _del_all_locks() -> None:
    _acquired_locks().clear()


def _get_lock_keys() -> list[str]:
    return list(_acquired_locks())


def _has_lock(name: str) -> bool:
    return name in _acquired_locks()


@contextmanager
def locked(path: Path | str, blocking: bool = True) -> Iterator[None]:
    acquired = acquire_lock(path, blocking)
    try:
        yield
    finally:
        if acquired:
            release_lock(path)


def acquire_lock(path: Path | str, blocking: bool = True) -> bool:
    """Obtain physical file lock on a file.
    If the file is already registered, then  done do nothing and return False.
    Otherwise, locks file physically, register file in global variable and returns True"""
    if not isinstance(path, Path):
        path = Path(path)

    if have_lock(path):
        return False

    logger.debug("Trying to acquire lock on %s", path)
    # Create file (and base dir) for locking if not existent yet
    path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)

    while True:
        with _open_lock_file(path) as fd:
            fcntl.flock(fd, flags)
            # Handle the case where the file has been renamed in the meantime
            with _open_lock_file(path) as fd_new:
                if os.path.sameopenfile(fd, fd_new):
                    _set_lock(str(path), os.dup(fd))
                    logger.debug("Got lock on %s", path)
                    return True


@contextmanager
def _open_lock_file(path: os.PathLike) -> Iterator[int]:
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0o660)
        yield fd
    finally:
        if fd is not None:
            os.close(fd)


@contextmanager
def try_locked(path: Path | str) -> Iterator[bool]:
    acquired = try_acquire_lock(path)
    try:
        yield acquired
    finally:
        if acquired:
            release_lock(path)


def try_acquire_lock(path: Path | str) -> bool:
    try:
        return acquire_lock(path, blocking=False)
    except OSError as e:
        if e.errno != errno.EAGAIN:  # Try again
            raise
        return False


def release_lock(path: Path | str) -> None:
    if not isinstance(path, Path):
        path = Path(path)

    if not have_lock(path):
        return  # no unlocking needed

    logger.debug("Releasing lock on %s", path)
    if (fd := _get_lock(str(path))) is None:
        return

    try:
        os.close(fd)
    except OSError as e:
        if e.errno != errno.EBADF:  # Bad file number
            raise
    finally:
        _del_lock(str(path))
        logger.debug("Released lock on %s", path)


def have_lock(path: str | Path) -> bool:
    return _has_lock(str(path))


def release_all_locks() -> None:
    logger.debug("Releasing all locks")
    logger.debug("Acquired locks: %r", _acquired_locks())
    for path in _get_lock_keys():
        release_lock(path)
    _del_all_locks()


@contextmanager
def leave_locked_unless_exception(path: str | Path) -> Iterator[None]:
    """Contextmanager to lock a file, and release the lock if an exception occurs.

    If no exception occurs, the file is left behind locked.
    Clearly this hellish maneuver should be removed from the code base.
    In order to make this happen, every lock shall itself only be used as a context-manager.
    """
    try:
        acquire_lock(path)
        yield
    except Exception:
        release_lock(path)
        raise


@contextmanager
def cleanup_locks() -> Iterator[None]:
    """Context-manager to release all memorized locks at the end of the block.

    This is a hack which should be removed.
    In order to make this happen, every lock shall itself only be used as a context-manager.
    """
    try:
        yield
    finally:
        try:
            release_all_locks()
        except Exception:
            logger.exception("Error while releasing locks after block.")
            raise
