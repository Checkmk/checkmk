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

import six


# never used directly in the code. Just some wrapper to make all of our
# exceptions handleable with one call
class MKException(Exception):
    # TODO: Remove this method after Python 3 migration.
    # NOTE: In Python 2 the return type is WRONG, we should return str.
    def __str__(self):
        # not-yet-a-type: () -> six.text_type
        """
        Python 3:
        - No args:
          >>> str(Exception())
          ''

        - Bytes input:
          >>> str(Exception(b"h\xc3\xa9 \xc3\x9f\xc3\x9f"))
          "b'h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f'"

        - Unicode input:
          >>> str(Exception("hé ßß"))
          'hé ßß'

        - Multiple args:
          >>> str(Exception(b"h\xc3\xa9 \xc3\x9f\xc3\x9f", 123, "hé ßß"))
          "(b'h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f', 123, 'hé ßß')"
        """

        if not self.args:
            return six.text_type("")

        if len(self.args) == 1:
            arg = self.args[0]
            if isinstance(arg, six.binary_type):
                # Python 3 immediately returns repr of bytestr but we try to decode first.
                # We always return a unicode str.
                try:
                    return arg.decode("utf-8")
                except UnicodeDecodeError:
                    return u"b%s" % repr(arg)
            return six.text_type(arg)

        return six.text_type(self.args)


class MKGeneralException(MKException):
    pass


# This exception is raises when the current program execution should be
# terminated. For example it is raised by the SIGINT signal handler to
# propagate the termination up the callstack.
# This should be raised in all cases where the program termination is a
# "normal" case and no exception handling like printing a stack trace
# nor an error message should be done. The program is stopped with
# exit code 0.
class MKTerminate(MKException):
    pass


# This is raised to print an error message and then end the program.
# The program should catch this at top level and end exit the program
# with exit code 3, in order to be compatible with monitoring plugin API.
class MKBailOut(MKException):
    pass


# This exception is raised when a previously configured timeout is reached.
# It is used during keepalive mode. It is also used by the automations
# which have a timeout set.
class MKTimeout(MKException):
    pass
