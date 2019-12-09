#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

import os
import sys
import ctypes
import ctypes.util
from contextlib import contextmanager
from typing import Generator  # pylint: disable=unused-import

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path

import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException


def daemonize():
    # type: () -> None
    # do the UNIX double-fork magic, see Stevens' "Advanced
    # Programming in the UNIX Environment" for details (ISBN 0201563177)
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("Fork failed (#1): %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # decouple from parent environment
    # chdir -> don't prevent unmounting...
    os.chdir("/")

    # Create new process group with the process as leader
    os.setsid()

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("Fork failed (#2): %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    sys.stdout.flush()
    sys.stderr.flush()

    si = os.open("/dev/null", os.O_RDONLY)
    so = os.open("/dev/null", os.O_WRONLY)
    os.dup2(si, 0)
    os.dup2(so, 1)
    os.dup2(so, 2)
    os.close(si)
    os.close(so)


def closefrom(lowfd):
    # type: (int) -> None
    """Closes all file descriptors starting with "lowfd", ignoring errors

    Deletes all open file descriptors greater than or equal to lowfd from the
    per-process object reference table.  Any errors encountered while closing
    file descriptors are ignored.

    Difference to os.closerange() is that this automatically determines the
    highest fd number to close.
    """
    try:
        highfd = os.sysconf("SC_OPEN_MAX")
    except ValueError:
        highfd = 1024

    os.closerange(lowfd, highfd)


def lock_with_pid_file(path):
    # type: (Path) -> None
    """
    Use this after daemonizing or in foreground mode to ensure there is only
    one process running.
    """
    if not store.try_aquire_lock(str(path)):
        raise MKGeneralException("Failed to aquire PID file lock: "
                                 "Another process is already running")

    # Now that we have the lock we are allowed to write our pid to the file.
    # The pid can then be used by the init script.
    with path.open("w", encoding="utf-8") as f:
        f.write(u"%d\n" % os.getpid())


def _cleanup_locked_pid_file(path):
    # type: (Path) -> None
    """Cleanup the lock + file acquired by the function above"""
    if not store.have_lock(str(path)):
        return

    store.release_lock(str(path))

    try:
        path.unlink()
    except OSError:
        pass


@contextmanager
def pid_file_lock(path):
    # type: (Path) -> Generator[None, None, None]
    """Context manager for PID file based locking"""
    lock_with_pid_file(path)
    try:
        yield
    finally:
        _cleanup_locked_pid_file(path)


def set_cmdline(cmdline):
    # type: (bytes) -> None
    """
    Change the process name and process command line on of the running process
    This works at least with Python 2.x on Linux
    """
    argv = ctypes.POINTER(ctypes.c_char_p)()
    argc = ctypes.c_int()
    ctypes.pythonapi.Py_GetArgcArgv(ctypes.byref(argc), ctypes.byref(argv))
    # mypy: The type is not detected correctly
    cmdlen = sum([len(argv[i]) for i in range(argc.value)]) + argc.value  # type: ignore
    # TODO: This can probably be simplified...
    _new_cmdline = ctypes.c_char_p(cmdline.ljust(cmdlen, b'\0'))

    set_procname(cmdline)


def set_procname(cmdline):
    # type: (bytes) -> None
    """
    Change the process name of the running process
    This works at least with Python 2.x on Linux
    """
    lib = ctypes.util.find_library('c')
    if not lib:
        return
    libc = ctypes.cdll.LoadLibrary(lib)

    #argv = ctypes.POINTER(ctypes.c_char_p)()

    # replace the command line, which is available via /proc/<pid>/cmdline.
    # This is .e.g used by ps
    #libc.memcpy(argv.contents, new_cmdline, cmdlen)

    # replace the prctl name, which is available via /proc/<pid>/status.
    # This is for example used by top and killall
    #libc.prctl(15, new_cmdline, 0, 0, 0)

    name_buffer = ctypes.create_string_buffer(len(cmdline) + 1)
    name_buffer.value = cmdline
    libc.prctl(15, ctypes.byref(name_buffer), 0, 0, 0)
