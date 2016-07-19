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

import fcntl
import os
import tempfile

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
