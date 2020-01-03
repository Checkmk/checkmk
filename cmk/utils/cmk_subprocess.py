#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
"""
This module is a little wrapper for the Python 2 subprocess.Popen and
communicate method in order to allow the flag 'encoding' as Python 3 version
does. This can be removed after Python 3 migration.
"""

import sys
import subprocess

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
list2cmdline = subprocess.list2cmdline
call = subprocess.call
check_output = subprocess.check_output
CalledProcessError = subprocess.CalledProcessError

if sys.platform == "win32":
    CREATE_NEW_PROCESS_GROUP = subprocess.CREATE_NEW_PROCESS_GROUP
else:
    CREATE_NEW_PROCESS_GROUP = None

if sys.version_info[0] >= 3:
    Popen = subprocess.Popen

else:

    class Popen(subprocess.Popen):
        def __init__(
            self,
            args,
            bufsize=0,
            executable=None,
            stdin=None,
            stdout=None,
            stderr=None,
            preexec_fn=None,
            close_fds=False,
            shell=False,
            cwd=None,
            env=None,
            universal_newlines=False,
            startupinfo=None,
            creationflags=0,
            encoding=None,
        ):
            # NOTE: We need the pragma below because of a typeshed bug!
            super(Popen, self).__init__(  # type: ignore[call-arg]
                args,
                bufsize=bufsize,
                executable=executable,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                preexec_fn=preexec_fn,
                close_fds=close_fds,
                shell=shell,
                cwd=cwd,
                env=env,
                universal_newlines=universal_newlines,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )

            # Cannot decode streams from args as Python 3 subprocess module does:
            #   py2 subprocess uses os.fdopen
            #   py3 subprocess uses io.open

            if universal_newlines:
                # We don't need this arg on Checkmk servers:
                #   Lines may be terminated by any of '\n', the Unix end-of-line
                #   convention, '\r', the old Macintosh convention or '\r\n', the
                #   Windows convention. All of these external representations are
                #   seen as '\n' by the Python program.
                raise AttributeError("Do not use 'universal_newlines'")

            self.encoding = encoding

        def communicate(self, input=None):  # pylint: disable=redefined-builtin
            # Python 2:
            # The optional input argument should be a
            # string to be sent to the child process, or None, if no data
            # should be sent to the child.

            # Python 3:
            # The optional "input" argument should be data to be sent to the
            # child process (if self.universal_newlines is True, this should
            # be a string; if it is False, "input" should be bytes), or
            # None, if no data should be sent to the child.
            # By default, all communication is in bytes, and therefore any
            # "input" should be bytes, and the (stdout, stderr) will be bytes.
            # If in text mode (indicated by self.text_mode), any "input" should
            # be a string, and (stdout, stderr) will be strings decoded
            # according to locale encoding, or by "encoding" if set. Text mode
            # is triggered by setting any of text, encoding, errors or
            # universal_newlines.

            if input is not None:
                if self.encoding:
                    if not isinstance(input, unicode):
                        # As Python 3 subprocess does:
                        raise AttributeError("'bytes' object has no attribute 'encode'")
                    input = input.encode(self.encoding)
                else:
                    if not isinstance(input, str):
                        # As Python 3 subprocess does:
                        raise TypeError("a bytes-like object is required, not 'str'")

            stdout, stderr = super(Popen, self).communicate(input=input)

            if self.encoding:
                return (None if stdout is None else stdout.decode(self.encoding),
                        None if stderr is None else stderr.decode(self.encoding))
            return (stdout, stderr)
