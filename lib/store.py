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

import ast
import fcntl
import os
import pprint
import tempfile
import time

from .exceptions import MKGeneralException

# TODO: Please note that this is still experimental.

# TODO: Clean this up one day by using the way recommended by gettext.
# (See https://docs.python.org/2/library/gettext.html). For this we
# need the path to the locale files here.
try:
    _
except NameError:
    _ = lambda x: x # Fake i18n when not available


# Simple class to offer locked file access via flock for cross process locking
class LockedOpen(object):
    def __init__(self, path, *args, **kwargs):
        self._path        = path
        self._open_args   = args
        self._open_kwargs = kwargs
        self._file_obj    = None


    def __enter__(self):
        # If not existant, create the file that the open can not fail in
        # read mode and the lock is possible
        if not os.path.exists(self._path):
            file(self._path, "a+")

        f = file(self._path, *self._open_args, **self._open_kwargs)

    	# Handle the case where the file has been renamed while waiting
        while True:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            fnew = file(self._path, *self._open_args, **self._open_kwargs)
            if os.path.sameopenfile(f.fileno(), fnew.fileno()):
                fnew.close()
                break
            else:
                f.close()
                f = fnew

        self._file_obj = f
        self._file_obj.__enter__()
        return self


    def __exit__(self, _exc_type, _exc_value, _traceback):
        result = self._file_obj.__exit__(_exc_type, _exc_value, _traceback)
        return result


    def __getattr__(self, name):
        return getattr(self._file_obj, name)


# This class offers locked file opening. Read operations are made on the
# locked file. All write operation go to a temporary file which replaces
# the locked file while closing the object.
class LockedOpenWithTempfile(LockedOpen):
    def __init__(self, name, mode):
        super(LockedOpenWithTempfile, self).__init__(name, "r")
        self._new_file_obj = None
        self._new_file_mode = mode


    def __enter__(self):
        super(LockedOpenWithTempfile, self).__enter__()
        self._new_file_obj = tempfile.NamedTemporaryFile(self._new_file_mode,
                                dir=os.path.dirname(self._path),
                                prefix=os.path.basename(self._path)+"_tmp",
                                delete=False)
        self._new_file_obj.__enter__()
        return self


    def write(self, txt):
        self._new_file_obj.write(txt)


    def writelines(self, seq):
        self._new_file_obj.writelines(seq)


    def __exit__(self, _exc_type, _exc_value, _traceback):
        self._new_file_obj.__exit__(_exc_type, _exc_value, _traceback)
        os.rename(self._new_file_obj.name, self._path)
        return super(LockedOpenWithTempfile, self).__exit__(_exc_type, _exc_value, _traceback)


open = LockedOpenWithTempfile


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

# This function generalizes reading from a .mk configuration file. It is basically meant to
# generalize the exception handling for all file IO. This function handles all those files
# that are read with execfile().
def load_mk_file(path, default=None, lock=False):
    if default == None:
        raise MKGeneralException(_("You need to provide a config dictionary to merge with the "
                                   "read configuration. The dictionary should have all expected "
                                   "keys and their default values set."))

    if lock:
        aquire_lock(path)

    try:
        execfile(path, globals(), default)
        return default
    except IOError, e:
        if e.errno == 2: # IOError: [Errno 2] No such file or directory
            return default
        else:
            raise

    except Exception, e:
        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot read configuration file \"%s\": %s") % (path, e))


# A simple wrapper for cases where you only have to read a single value from a .mk file.
def load_from_mk_file(path, key, default, **kwargs):
    return load_mk_file(path, {key: default}, **kwargs)[key]


def save_mk_file(path, mk_content):
    content = "# Written by Check_MK store (%s)\n\n" % \
              time.strftime("%Y-%m-%d %H:%M:%S")
    content += mk_content
    content += "\n"
    save_file(path, content)


# Handle .mk files that are only holding a python data structure and often
# directly read via file/open and then parsed using eval.
# TODO: Consolidate with load_mk_file?
def load_data_from_file(path, default=None, lock=False):
    if lock:
        aquire_lock(path)

    try:
        return ast.literal_eval(file(path).read())
    except IOError, e:
        if e.errno == 2: # IOError: [Errno 2] No such file or directory
            return default
        else:
            raise

    except Exception, e:
        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot read file \"%s\": %s") % (path, e))


# A simple wrapper for cases where you want to store a python data
# structure that is then read by load_data_from_file() again
def save_data_to_file(path, data):
    save_file(path, "%r\n" % data)


# Saving assumes a locked destination file (usually done by loading code)
# Then the new file is written to a temporary file and moved to the target path
def save_file(path, content, mode=0660):
    try:
        tmp_path = None
        with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(path),
                                         prefix=os.path.basename(path)+".new",
                                         delete=False) as tmp:
            tmp_path = tmp.name
            os.chmod(tmp_path, mode)
            tmp.write(content)

        os.rename(tmp_path, path)

    except Exception, e:
        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot write configuration file \"%s\": %s") % (path, e))

    finally:
        release_lock(path)


# A simple wrapper for cases where you only have to write a single value to a .mk file.
def save_to_mk_file(path, key, value):
    if type(value) == dict:
        formated = "%s.update(%s)" % (key, pprint.pformat(value))
    else:
        formated = "%s += %s" % (key, pprint.pformat(value))

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

g_aquired_locks = []
g_locked_paths  = []

def aquire_lock(path):
    if path in g_locked_paths:
        return True # No recursive locking

    # Create file (and base dir) for locking if not existant yet
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path), mode=0770)

    fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0660)

    # Handle the case where the file has been renamed in the meantime
    while True:
        fcntl.flock(fd, fcntl.LOCK_EX)
        fd_new = os.open(path, os.O_RDONLY | os.O_CREAT, 0660)
        if os.path.sameopenfile(fd, fd_new):
            os.close(fd_new)
            break
        else:
            os.close(fd)
            fd = fd_new

    g_aquired_locks.append((path, fd))
    g_locked_paths.append(path)


def release_lock(path):
    if path not in g_locked_paths:
        return # no unlocking needed

    for lock_path, fd in g_aquired_locks:
        if lock_path == path:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            g_aquired_locks.remove((lock_path, fd))

    g_locked_paths.remove(path)


def have_lock(path):
    return path in g_locked_paths


def release_all_locks():
    global g_aquired_locks, g_locked_paths

    for path, fd in g_aquired_locks:
        os.close(fd)

    g_aquired_locks = []
    g_locked_paths  = []
