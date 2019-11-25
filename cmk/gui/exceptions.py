#!/usr/bin/python
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

import httplib
from typing import Optional, Text  # pylint: disable=unused-import

from werkzeug.http import HTTP_STATUS_CODES

from cmk.utils.exceptions import (
    MKException,
    MKGeneralException,
    MKTimeout,
)


class RequestTimeout(MKTimeout):
    """Is raised from the alarm signal handler (handle_request_timeout()) to
    abort page processing before the system apache times out."""
    pass


class FinalizeRequest(MKException):
    """Is used to end the HTTP request processing from deeper code levels"""
    def __init__(self, code):
        # type: (int) -> None
        super(FinalizeRequest, self).__init__("%d %s" % (code, HTTP_STATUS_CODES[code]))
        self.status = code


class HTTPRedirect(FinalizeRequest):
    """Is used to end the HTTP request processing from deeper code levels
    and making the client request another page after receiving the response."""
    def __init__(self, url):
        # type: (str) -> None
        super(HTTPRedirect, self).__init__(httplib.FOUND)
        self.url = url  # type: str


class MKAuthException(MKException):
    pass


class MKUnauthenticatedException(MKGeneralException):
    pass


class MKConfigError(MKException):
    pass


class MKUserError(MKException):
    def __init__(self, varname, message):
        # type: (Optional[str], Text) -> None
        self.varname = varname  # type: Optional[str]
        self.message = message  # type: Text
        super(MKUserError, self).__init__(varname, message)

    def __str__(self):
        return self.message


class MKInternalError(MKException):
    pass
