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

# TODO: Inherit from cmk.MKGeneralException?

import traceback

from cmk.utils.exceptions import (
    MKException,
    MKGeneralException,
)


class MKAgentError(MKException):
    pass


class MKIPAddressLookupError(MKGeneralException):
    pass


class MKEmptyAgentData(MKAgentError):
    pass


class MKParseFunctionError(MKException):
    def __init__(self, exception_type, exception, backtrace):
        self.exception_type = exception_type
        self.exception = exception
        self.backtrace = backtrace
        super(MKParseFunctionError, self).__init__(self, exception_type, exception, backtrace)

    def exc_info(self):
        return self.exception_type, self.exception, self.backtrace

    def __str__(self):
        return "%r\n%s" % (self.exception, "".join(traceback.format_tb(self.backtrace)))


class MKSNMPError(MKException):
    pass


class MKSkipCheck(MKException):
    pass
