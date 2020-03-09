#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
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

        if sys.version_info[0] >= 3:
            return super(MKException, self).__str__()

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
