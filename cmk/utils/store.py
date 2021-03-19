#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module cares about Check_MK's file storage accessing. Most important
functionality is the locked file opening realized with the File() context
manager."""

import ast
from contextlib import contextmanager
import errno
import fcntl
import logging
import os
from pathlib import Path
import pprint
import tempfile
from typing import Any, Union, Dict, Iterator, Optional, AnyStr, cast

from six import ensure_binary

from cmk.utils.exceptions import MKGeneralException, MKTimeout, MKTerminate
from cmk.utils.i18n import _
from cmk.utils.paths import default_config_dir

logger = logging.getLogger("cmk.store")

# TODO: Make all methods handle paths the same way. e.g. mkdir() and makedirs()
# care about encoding a path to UTF-8. The others don't to that.

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
    return default_config_dir + "/multisite.mk"


@contextmanager
def lock_checkmk_configuration() -> Iterator[None]:
    path = configuration_lockfile()
    aquire_lock(path)
    try:
        yield
    finally:
        release_lock(path)


# TODO: Use lock_checkmk_configuration() and nuke this!
def lock_exclusive() -> None:
    aquire_lock(configuration_lockfile())


#.
#   .--Directories---------------------------------------------------------.
#   |           ____  _               _             _                      |
#   |          |  _ \(_)_ __ ___  ___| |_ ___  _ __(_) ___  ___            |
#   |          | | | | | '__/ _ \/ __| __/ _ \| '__| |/ _ \/ __|           |
#   |          | |_| | | | |  __/ (__| || (_) | |  | |  __/\__ \           |
#   |          |____/|_|_|  \___|\___|\__\___/|_|  |_|\___||___/           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some small wrappers around the python standard directory handling    |
#   | functions.                                                           |
#   '----------------------------------------------------------------------'


def mkdir(path: Union[Path, str], mode: int = 0o770) -> None:
    if not isinstance(path, Path):
        path = Path(path)
    path.mkdir(mode=mode, exist_ok=True)


def makedirs(path: Union[Path, str], mode: int = 0o770) -> None:
    if not isinstance(path, Path):
        path = Path(path)
    path.mkdir(mode=mode, exist_ok=True, parents=True)


#.
#   .--.mk Configs---------------------------------------------------------.
#   |                     _       ____             __ _                    |
#   |           _ __ ___ | | __  / ___|___  _ __  / _(_) __ _ ___          |
#   |          | '_ ` _ \| |/ / | |   / _ \| '_ \| |_| |/ _` / __|         |
#   |         _| | | | | |   <  | |__| (_) | | | |  _| | (_| \__ \         |
#   |        (_)_| |_| |_|_|\_\  \____\___/|_| |_|_| |_|\__, |___/         |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+
#   | Loading and saving of .mk configuration files                        |
#   '----------------------------------------------------------------------'

# TODO: These functions could handle paths unicode > str conversion. This would make
#       the using code again shorter in some cases. It would not have to care about
#       encoding anymore.


# This function generalizes reading from a .mk configuration file. It is basically meant to
# generalize the exception handling for all file IO. This function handles all those files
# that are read with exec().
def load_mk_file(path: Union[Path, str], default: Any = None, lock: bool = False) -> Any:
    if not isinstance(path, Path):
        path = Path(path)

    if default is None:
        raise MKGeneralException(
            _("You need to provide a config dictionary to merge with the "
              "read configuration. The dictionary should have all expected "
              "keys and their default values set."))

    if lock:
        aquire_lock(path)

    try:
        try:
            with path.open(mode="rb") as f:
                exec(f.read(), globals(), default)
        except IOError as e:
            if e.errno != errno.ENOENT:  # No such file or directory
                raise
        return default

    except (MKTerminate, MKTimeout):
        raise
    except Exception as e:
        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot read configuration file \"%s\": %s") % (path, e))


# A simple wrapper for cases where you only have to read a single value from a .mk file.
def load_from_mk_file(path: Union[Path, str], key: str, default: Any, lock: bool = False) -> Any:
    return load_mk_file(path, {key: default}, lock=False)[key]


def save_mk_file(path: Union[Path, str], mk_content: str, add_header: bool = True) -> None:
    content = ""

    if add_header:
        content += "# Written by Checkmk store\n\n"

    content += mk_content
    content += "\n"
    save_file(path, content)


# A simple wrapper for cases where you only have to write a single value to a .mk file.
def save_to_mk_file(path: Union[Path, str],
                    key: str,
                    value: Any,
                    pprint_value: bool = False) -> None:
    format_func = repr
    if pprint_value:
        format_func = pprint.pformat

    # mypy complains: "[mypy:] Cannot call function of unknown type"
    if isinstance(value, dict):
        formated = "%s.update(%s)" % (key, format_func(value))
    else:
        formated = "%s += %s" % (key, format_func(value))

    save_mk_file(path, formated)


#.
#   .--load/save-----------------------------------------------------------.
#   |             _                 _    __                                |
#   |            | | ___   __ _  __| |  / /__  __ ___   _____              |
#   |            | |/ _ \ / _` |/ _` | / / __|/ _` \ \ / / _ \             |
#   |            | | (_) | (_| | (_| |/ /\__ \ (_| |\ V /  __/             |
#   |            |_|\___/ \__,_|\__,_/_/ |___/\__,_| \_/ \___|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# Handle .mk files that are only holding a python data structure and often
# directly read via file/open and then parsed using eval.
# TODO: Consolidate with load_mk_file?
def load_object_from_file(path: Union[Path, str], default: Any = None, lock: bool = False) -> Any:
    content = cast(str, _load_data_from_file(path, lock=lock, encoding="utf-8"))
    if not content:
        return default
    return ast.literal_eval(content)


def load_text_from_file(path: Union[Path, str], default: str = u"", lock: bool = False) -> str:
    content = cast(str, _load_data_from_file(path, lock=lock, encoding="utf-8"))
    if not content:
        return default
    return content


def load_bytes_from_file(path: Union[Path, str], default: bytes = b"", lock: bool = False) -> bytes:
    content = cast(bytes, _load_data_from_file(path, lock=lock))
    if not content:
        return default
    return content


# TODO: This function has to die! Its return type depends on the value of the
# encoding parameter, which doesn't work at all with mypy and various APIs like
# ast.literal_eval. As a workaround, we use casts, but this isn't a real
# solution....
def _load_data_from_file(path: Union[Path, str],
                         lock: bool = False,
                         encoding: Optional[str] = None) -> Union[None, str, bytes]:
    if not isinstance(path, Path):
        path = Path(path)

    if lock:
        aquire_lock(path)

    try:
        try:
            return path.read_text(encoding=encoding) if encoding else path.read_bytes()
        except IOError as e:
            if e.errno != errno.ENOENT:  # No such file or directory
                raise
            return None

    except (MKTerminate, MKTimeout):
        if lock:
            release_lock(path)
        raise

    except Exception as e:
        if lock:
            release_lock(path)

        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot read file \"%s\": %s") % (path, e))


# A simple wrapper for cases where you want to store a python data
# structure that is then read by load_data_from_file() again
def save_object_to_file(path: Union[Path, str], data: Any, pretty: bool = False) -> None:
    if pretty:
        try:
            formatted_data = pprint.pformat(data)
        except UnicodeDecodeError:
            # When writing a dict with unicode keys and normal strings with garbled
            # umlaut encoding pprint.pformat() fails with UnicodeDecodeError().
            # example:
            #   pprint.pformat({'Z\xc3\xa4ug': 'on',  'Z\xe4ug': 'on', u'Z\xc3\xa4ugx': 'on'})
            # Catch the exception and use repr() instead
            formatted_data = repr(data)
    else:
        formatted_data = repr(data)
    save_file(path, "%s\n" % formatted_data)


def save_text_to_file(path: Union[Path, str], content: str, mode: int = 0o660) -> None:
    if not isinstance(content, str):
        raise TypeError("content argument must be Text, not bytes")
    _save_data_to_file(path, content.encode("utf-8"), mode)


def save_bytes_to_file(path: Union[Path, str], content: bytes, mode: int = 0o660) -> None:
    if not isinstance(content, bytes):
        raise TypeError("content argument must be bytes, not Text")
    _save_data_to_file(path, content, mode)


def save_file(path: Union[Path, str], content: AnyStr, mode: int = 0o660) -> None:
    # Just to be sure: ensure_binary
    _save_data_to_file(path, ensure_binary(content), mode=mode)


# Saving assumes a locked destination file (usually done by loading code)
# Then the new file is written to a temporary file and moved to the target path
def _save_data_to_file(path: Union[Path, str], content: bytes, mode: int = 0o660) -> None:
    if not isinstance(path, Path):
        path = Path(path)

    tmp_path = None
    try:
        # Normally the file is already locked (when data has been loaded before with lock=True),
        # but lock it just to be sure we have the lock on the file.
        #
        # Please note that this already creates the file with 0 bytes (in case it is missing).
        aquire_lock(path)

        with tempfile.NamedTemporaryFile("wb",
                                         dir=str(path.parent),
                                         prefix=".%s.new" % path.name,
                                         delete=False) as tmp:

            tmp_path = tmp.name
            os.chmod(tmp_path, mode)
            tmp.write(content)

            # The goal of the fsync would be to ensure that there is a consistent file after a
            # crash. Without the fsync it may happen that the file renamed below is just an empty
            # file. That may lead into unexpected situations during loading.
            #
            # Don't do a fsync here because this may run into IO performance issues. Even when
            # we can specify the fsync on a fd, the disk cache may be flushed completely because
            # the disk does not know anything about fds, only about blocks.
            #
            # For Checkmk 1.4 we can not introduce a good solution for this, because the changes
            # would affect too many parts of Checkmk with possible new issues. For the moment we
            # stick with the IO behaviour of previous Checkmk versions.
            #
            # In the future we'll find a solution to deal better with OS crash recovery situations.
            # for example like this:
            #
            # TODO(lm): The consistency of the file will can be ensured using copies of the
            # original file which are made before replacing it with the new one. After first
            # successful loading of the just written fille the possibly existing copies of this
            # file are deleted.
            # We can archieve this by calling os.link() before the os.rename() below. Then we need
            # to define in which situations we want to check out the backup open(s) and in which
            # cases we can savely delete them.
            #tmp.flush()
            #os.fsync(tmp.fileno())

        os.rename(tmp_path, str(path))

    except (MKTerminate, MKTimeout):
        raise
    except Exception as e:
        # In case an exception happens during saving cleanup the tempfile created for writing
        try:
            if tmp_path:
                os.unlink(tmp_path)
        except IOError as e2:
            if e2.errno != errno.ENOENT:  # No such file or directory
                raise

        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot write configuration file \"%s\": %s") % (path, e))

    finally:
        release_lock(path)


#.
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

_acquired_locks: Dict[str, int] = {}


@contextmanager
def locked(path: Union[Path, str], blocking: bool = True) -> Iterator[None]:
    try:
        aquire_lock(path, blocking)
        yield
    finally:
        release_lock(path)


def aquire_lock(path: Union[Path, str], blocking: bool = True) -> None:
    if not isinstance(path, Path):
        path = Path(path)

    if have_lock(path):
        return  # No recursive locking

    logger.debug("Try aquire lock on %s", path)

    # Create file (and base dir) for locking if not existant yet
    makedirs(path.parent, mode=0o770)

    fd = os.open(str(path), os.O_RDONLY | os.O_CREAT, 0o660)

    # Handle the case where the file has been renamed in the meantime
    while True:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB

        try:
            fcntl.flock(fd, flags)
        except IOError:
            os.close(fd)
            raise

        fd_new = os.open(str(path), os.O_RDONLY | os.O_CREAT, 0o660)
        if os.path.sameopenfile(fd, fd_new):
            os.close(fd_new)
            break
        os.close(fd)
        fd = fd_new

    _acquired_locks[str(path)] = fd
    logger.debug("Got lock on %s", path)


@contextmanager
def try_locked(path: Union[Path, str]) -> Iterator[bool]:
    try:
        yield try_aquire_lock(path)
    finally:
        release_lock(path)


def try_aquire_lock(path: Union[Path, str]) -> bool:
    try:
        aquire_lock(path, blocking=False)
        return True
    except IOError as e:
        if e.errno != errno.EAGAIN:  # Try again
            raise
        return False


def release_lock(path: Union[Path, str]) -> None:
    if not isinstance(path, Path):
        path = Path(path)

    if not have_lock(path):
        return  # no unlocking needed
    logger.debug("Releasing lock on %s", path)
    fd = _acquired_locks.get(str(path))
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError as e:
        if e.errno != errno.EBADF:  # Bad file number
            raise
    _acquired_locks.pop(str(path), None)
    logger.debug("Released lock on %s", path)


def have_lock(path: Union[str, Path]) -> bool:
    if isinstance(path, Path):
        path = str(path)

    return path in _acquired_locks


def release_all_locks() -> None:
    logger.debug("Releasing all locks")
    logger.debug("_acquired_locks: %r", _acquired_locks)
    for path in list(_acquired_locks.keys()):
        release_lock(path)
    _acquired_locks.clear()


@contextmanager
def cleanup_locks() -> Iterator[None]:
    """Context-manager to release all memorized locks at the end of the block.

    This is a hack which should be removed. In order to make this happen, every lock shall
    itself only be used as a context-manager.
    """
    try:
        yield
    finally:
        try:
            release_all_locks()
        except Exception:
            logger.exception("Error while releasing locks after block.")
            raise
