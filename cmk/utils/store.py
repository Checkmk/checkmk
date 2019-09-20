#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""This module cares about Check_MK's file storage accessing. Most important
functionality is the locked file opening realized with the File() context
manager."""

import sys
import ast
from contextlib import contextmanager
import errno
import fcntl
import logging
import os
import pprint
import tempfile
import time
from typing import Callable, Any, Union, Dict, Iterator, List  # pylint: disable=unused-import

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path

from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.i18n import _
from cmk.utils.paths import default_config_dir

logger = logging.getLogger("cmk.store")

# TODO: Make all methods handle paths the same way. e.g. mkdir() and makedirs()
# care about encoding a path to UTF-8. The others don't to that.

#.
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


def configuration_lockfile():
    # type: () -> str
    return default_config_dir + "/multisite.mk"


@contextmanager
def lock_checkmk_configuration():
    # type: () -> Iterator[None]
    path = configuration_lockfile()
    aquire_lock(path)
    try:
        yield
    finally:
        release_lock(path)


# TODO: Use lock_checkmk_configuration() and nuke this!
def lock_exclusive():
    # type: () -> None
    aquire_lock(configuration_lockfile())


#.
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


def mkdir(path, mode=0o770):
    # type: (str, int) -> None
    Path(path).mkdir(mode=mode, exist_ok=True)


def makedirs(path, mode=0o770):
    # type: (Union[Path, str], int) -> None
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
def load_mk_file(path, default=None, lock=False):
    # type: (str, Any, bool) -> Any
    if default is None:
        raise MKGeneralException(
            _("You need to provide a config dictionary to merge with the "
              "read configuration. The dictionary should have all expected "
              "keys and their default values set."))

    if lock:
        aquire_lock(path)

    try:
        try:
            exec (open(path).read(), globals(), default)
        except IOError as e:
            if e.errno != errno.ENOENT:  # No such file or directory
                raise
        return default

    except MKTimeout:
        raise
    except Exception as e:
        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot read configuration file \"%s\": %s") % (path, e))


# A simple wrapper for cases where you only have to read a single value from a .mk file.
def load_from_mk_file(path, key, default, lock=False):
    # type: (str, str, Any, bool) -> Any
    return load_mk_file(path, {key: default}, lock=False)[key]


def save_mk_file(path, mk_content, add_header=True):
    # type: (str, str, bool) -> None
    content = ""

    if add_header:
        content += "# Written by Check_MK store (%s)\n\n" % \
                    time.strftime("%Y-%m-%d %H:%M:%S")

    content += mk_content
    content += "\n"
    save_file(path, content)


# Handle .mk files that are only holding a python data structure and often
# directly read via file/open and then parsed using eval.
# TODO: Consolidate with load_mk_file?
def load_data_from_file(path, default=None, lock=False):
    # type: (str, Any, bool) -> Any
    if lock:
        aquire_lock(path)

    try:
        try:
            content = open(path).read().strip()
            if not content:
                # May be created empty during locking
                return default

            return ast.literal_eval(content)
        except IOError as e:
            if e.errno != errno.ENOENT:  # No such file or directory
                raise
            return default

    except MKTimeout:
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
def save_data_to_file(path, data, pretty=True):
    # type: (str, Any, bool) -> None
    if pretty:
        try:
            formated_data = pprint.pformat(data)
        except UnicodeDecodeError:
            # When writing a dict with unicode keys and normal strings with garbled
            # umlaut encoding pprint.pformat() fails with UnicodeDecodeError().
            # example:
            #   pprint.pformat({'Z\xc3\xa4ug': 'on',  'Z\xe4ug': 'on', u'Z\xc3\xa4ugx': 'on'})
            # Catch the exception and use repr() instead
            formated_data = repr(data)
    else:
        formated_data = repr(data)

    save_file(path, "%s\n" % formated_data)


# Saving assumes a locked destination file (usually done by loading code)
# Then the new file is written to a temporary file and moved to the target path
def save_file(path, content, mode=0o660):
    # type: (str, str, int) -> None
    tmp_path = None
    try:
        # Normally the file is already locked (when data has been loaded before with lock=True),
        # but lock it just to be sure we have the lock on the file.
        #
        # Please note that this already creates the file with 0 bytes (in case it is missing).
        aquire_lock(path)

        with tempfile.NamedTemporaryFile("w",
                                         dir=os.path.dirname(path),
                                         prefix=".%s.new" % os.path.basename(path),
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
            # For Check_MK 1.4 we can not introduce a good solution for this, because the changes
            # would affect too many parts of Check_MK with possible new issues. For the moment we
            # stick with the IO behaviour of previous Check_MK versions.
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

        os.rename(tmp_path, path)

    except MKTimeout:
        raise
    except Exception as e:
        # In case an exception happens during saving cleanup the tempfile created for writing
        try:
            if tmp_path:
                os.unlink(tmp_path)
        except IOError as e:
            if e.errno != errno.ENOENT:  # No such file or directory
                raise

        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot write configuration file \"%s\": %s") % (path, e))

    finally:
        release_lock(path)


# A simple wrapper for cases where you only have to write a single value to a .mk file.
def save_to_mk_file(path, key, value, pprint_value=False):
    # type: (str, str, Any, bool) -> None
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

_acquired_locks = {}  # type: Dict[str, int]


def aquire_lock(path, blocking=True):
    # type: (str, bool) -> None
    if have_lock(path):
        return  # No recursive locking

    logger.debug("Try aquire lock on %s", path.decode("utf-8"))

    # Create file (and base dir) for locking if not existant yet
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path), mode=0o770)

    fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0o660)

    # Handle the case where the file has been renamed in the meantime
    while True:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB

        fcntl.flock(fd, flags)
        fd_new = os.open(path, os.O_RDONLY | os.O_CREAT, 0o660)
        if os.path.sameopenfile(fd, fd_new):
            os.close(fd_new)
            break
        else:
            os.close(fd)
            fd = fd_new

    _acquired_locks[path] = fd
    logger.debug("Got lock on %s", path.decode("utf-8"))


def try_aquire_lock(path):
    # type: (str) -> bool
    try:
        aquire_lock(path, blocking=False)
        return True
    except IOError as e:
        if e.errno != errno.EAGAIN:  # Try again
            raise
        return False


def release_lock(path):
    # type: (str) -> None
    if not have_lock(path):
        return  # no unlocking needed
    logger.debug("Releasing lock on %s", path.decode("utf-8"))
    fd = _acquired_locks.get(path)
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError as e:
        if e.errno != errno.EBADF:  # Bad file number
            raise
    _acquired_locks.pop(path, None)
    logger.debug("Released lock on %s", path.decode("utf-8"))


def have_lock(path):
    # type: (str) -> bool
    return path in _acquired_locks


def release_all_locks():
    # type: () -> None
    logger.debug("Releasing all locks")
    logger.debug("_acquired_locks: %r", _acquired_locks)
    for path in list(_acquired_locks.iterkeys()):
        release_lock(path)
    _acquired_locks.clear()
