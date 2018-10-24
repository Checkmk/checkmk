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

from cmk.i18n import _


# never used directly in the code. Just some wrapper to make all of our
# exceptions handleable with one call
class MKException(Exception):
    # TODO: The comment and the method below are nonsense: If we want unicode,
    # it is __unicode__'s task. This just seems to be a workaround for incorrect
    # call sites confusing both kinds of strings. Sometimes returning a unicode
    # string below just asks for trouble when e.g. this is spliced into a byte
    # string, and it *is* a byte string when __str__ is called: Splicing into a
    # unicode string would call __unicode__.
    #
    # Do not use the Exception() __str__, because it uses str()
    # to convert the message. We want to keep unicode strings untouched
    # And don't use self.message, because older python versions don't
    # have this variable set. self.args[0] seems to be the most portable
    # way at the moment.
    def __str__(self):
        return self.args[0]


class MKGeneralException(MKException):
    def __init__(self, reason):
        self.reason = reason
        super(MKGeneralException, self).__init__(reason)

    def __str__(self):
        return self.reason

    def plain_title(self):
        return _("General error")

    def title(self):
        return _("Error")


# This exception is raises when the current program execution should be
# terminated. For example it is raised by the SIGINT signal handler to
# propagate the termination up the callstack.
# This should be raised in all cases where the program termination is a
# "normal" case and no exception handling like printing a stack trace
# nor an error message should be done. The program is stopped with
# exit code 0.
class MKTerminate(Exception):
    pass


# This is raised to print an error message and then end the program.
# The program should catch this at top level and end exit the program
# with exit code 3, in order to be compatible with monitoring plugin API.
class MKBailOut(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKBailOut, self).__init__(reason)

    def __str__(self):
        return self.reason
