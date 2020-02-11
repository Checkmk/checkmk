#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Text  # pylint: disable=unused-import
import six
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
        super(HTTPRedirect, self).__init__(six.moves.http_client.FOUND)
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
