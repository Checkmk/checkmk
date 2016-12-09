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
# TODO: Cleanup self.reason to use .args of standard exceptions

class MKAgentError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKAgentError, self).__init__(reason)
    def __str__(self):
        return self.reason



class MKParseFunctionError(Exception):
    def __init__(self, exception_type, exception, backtrace):
        self.exception_type = exception_type
        self.exception = exception
        self.backtrace = backtrace
        super(MKParseFunctionError, self).__init__(self, exception_type, exception, backtrace)

    def exc_info(self):
        return self.exception_type, self.exception, self.backtrace

    def __str__(self):
        return "%s\n%s" % (self.exception, self.backtrace)



class MKSNMPError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKSNMPError, self).__init__(reason)
    def __str__(self):
        return self.reason



class MKSkipCheck(Exception):
    pass



# This exception is raised when a previously configured timeout is reached.
# It is used during keepalive mode. It is also used by the automations
# which have a timeout set.
class MKTimeout(Exception):
    pass

