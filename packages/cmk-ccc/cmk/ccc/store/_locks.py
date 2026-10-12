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
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never, Literal

from cmk.ccc.exceptions import MKBailOut, MKTimeout
from cmk.ccc.i18n import _

__all__ = [
    "acquire_lock",
    "cleanup_locks",
    "have_lock",
    "lock_checkmk_configuration",
    "activation_lock",
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


@contextmanager
def lock_checkmk_configuration(lockfile: Path) -> Iterator[None]:
    try:
        acquire_lock(lockfile)
    except MKTimeout as e:
        raise MKTimeout(
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
        release_lock(lockfile)


# TODO: lock_checkmk_configuration is doing something similar. It looks like we
# should unify these both locks. But: The lock_checkmk_configuration is currently acquired by the
# GUI process. In case the GUI calls an automation process, we would have a dead lock of these two
# processes. We'll have to check whether or not we can move the locking.
@contextmanager
def activation_lock(main_mk_file: Path, mode: Literal["abort", "wait"] | None) -> Iterator[None]:
    """Try to acquire the activation lock and raise exception in case it was not possible"""
    match mode:
        case None:
            # TODO: We really should purge this strange case from being configurable
            yield None  # No locking at all
            return

        case "abort":
            with try_locked(main_mk_file) as result:
                if result is False:
                    raise MKBailOut("Other restart currently in progress. Aborting.")
                yield None
            return

        case "wait":
            with locked(main_mk_file):
                yield None
            return

        case _:
            assert_never(mode)


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


@dataclass
class _Lock:
    fd: int
    owner_pid: int
    held: bool = False


# This will hold our path to lock dicts in acquired_locks
_locks = threading.local()


def _acquired_locks() -> dict[Path, _Lock]:
    """Make access to global locking dict thread-safe.

    Only the thread which acquired the lock should see the file descriptor in the locking
    dictionary. In order to do this, the locking dictionary(*) is now an attribute on a
    threading.local() object, which has to be created at runtime. This decorator handles
    the creation of these dicts.

    (*) The dict is a mapping from path-name to the lock.
    """
    if not hasattr(_locks, "acquired_locks"):
        _locks.acquired_locks = {}
    acquired_locks: dict[Path, _Lock] = _locks.acquired_locks
    return acquired_locks


def _set_lock(path: Path, fd: int) -> _Lock:
    lock = _acquired_locks()[path] = _Lock(fd, os.getpid())
    return lock


def _get_lock(path: Path) -> int | None:
    if (lock := _acquired_locks().get(path)) is None:
        return None
    return lock.fd


def _del_lock(path: Path) -> None:
    _acquired_locks().pop(path, None)


def _get_lock_keys() -> list[Path]:
    return list(_acquired_locks())


def have_lock(path: Path) -> bool:
    return (lock := _acquired_locks().get(path)) is not None and lock.held


@contextmanager
def locked(path: Path, blocking: bool = True) -> Iterator[None]:
    acquired = acquire_lock(path, blocking)
    try:
        yield
    finally:
        if acquired:
            release_lock(path)


# Important: This function is NOT THREAD SAFE if used without an appropriate release_lock()
#            call inside the thread. Use locked() instead. If multiple threads work on the
#            same file, the entire process will hang indefinitely.
def acquire_lock(path: Path, blocking: bool = True) -> bool:
    """Obtain physical file lock on a file.
    If the file is already registered, then  done do nothing and return False.
    Otherwise, locks file physically, register file in global variable and returns True"""
    if (lock := _acquired_locks().get(path)) is not None:
        if lock.held:
            return False
        # An interrupted release_lock() left the lock registered: finish its release first
        release_lock(path)

    logger.debug("Trying to acquire lock on %(path)s", {"path": path})
    # Create file (and base dir) for locking if not existent yet
    path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)

    while True:
        fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0o660)
        try:
            # Register before locking and inside the try: whatever interrupts us from here
            # on, the except clause below unregisters and closes the fd again.
            lock = _set_lock(path, fd)
            fcntl.flock(fd, flags)
            if os.path.samestat(os.fstat(fd), os.stat(path)):
                lock.held = True
                logger.debug("Got lock on %(path)s", {"path": path})
                return True
        except FileNotFoundError:
            pass  # deleted in the meantime, retry
        except BaseException:
            release_lock(path)
            raise
        release_lock(path)  # renamed or deleted in the meantime, retry


@contextmanager
def try_locked(path: Path) -> Iterator[bool]:
    acquired = try_acquire_lock(path)
    try:
        yield acquired
    finally:
        if acquired:
            release_lock(path)


def try_acquire_lock(path: Path) -> bool:
    try:
        return acquire_lock(path, blocking=False)
    except OSError as e:
        if e.errno != errno.EAGAIN:  # Try again
            raise
        return False


def release_lock(path: Path) -> None:
    if (lock := _acquired_locks().get(path)) is None:
        return

    logger.debug("Releasing lock on %(path)s", {"path": path})
    # Mark the lock as not held, unlock while the fd is still registered, then unregister,
    # then close. An interruption at any point leaves either a registered fd, which the next
    # acquire_lock() of the path, release_lock() or release_all_locks() releases, or an
    # unlocked, unregistered fd (a harmless fd leak). It never leaves a held lock without an
    # owner, a registered number that was already closed or a registered lock which is
    # reported as held but is not.
    lock.held = False
    # A forked child inherits the fd, which shares the lock with its parent. The child only
    # closes its copy, so the parent keeps the lock.
    if lock.owner_pid == os.getpid():
        try:
            fcntl.flock(lock.fd, fcntl.LOCK_UN)
        except OSError as e:
            if e.errno != errno.EBADF:
                raise
    _del_lock(path)
    try:
        os.close(lock.fd)
    except OSError as e:
        if e.errno != errno.EBADF:
            raise
    logger.debug("Released lock on %(path)s", {"path": path})


def release_all_locks() -> None:
    logger.debug("Releasing all acquired locks: %(locks)r", {"locks": _acquired_locks()})
    for path in _get_lock_keys():
        release_lock(path)


@contextmanager
def leave_locked_unless_exception(path: Path) -> Iterator[None]:
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
