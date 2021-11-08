#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import http.client
from typing import Optional

from werkzeug.http import HTTP_STATUS_CODES

from cmk.utils.exceptions import MKException, MKGeneralException, MKTimeout


class RequestTimeout(MKTimeout):
    """Is raised from the alarm signal handler (handle_request_timeout()) to
    abort page processing before the system apache times out."""


class MKHTTPException(MKException):
    status = 400


class FinalizeRequest(MKException):
    """Is used to end the HTTP request processing from deeper code levels"""

    def __init__(self, code: int) -> None:
        super().__init__("%d %s" % (code, HTTP_STATUS_CODES[code]))
        self.status = code


class HTTPRedirect(FinalizeRequest):
    """Is used to end the HTTP request processing from deeper code levels
    and making the client request another page after receiving the response."""

    status = 302

    def __init__(self, url: str, code: int = http.client.FOUND) -> None:
        super().__init__(code)
        self.url: str = url


class MKAuthException(MKHTTPException):
    status = 401


class MKUnauthenticatedException(MKGeneralException):
    pass


class MKConfigError(MKHTTPException):
    status = 400


class MKUserError(MKHTTPException):
    def __init__(
        self,
        varname: Optional[str],
        message: str,
        status: int = 400,
    ) -> None:
        self.varname: Optional[str] = varname
        self.message: str = message
        self.status: int = status
        super().__init__(varname, message)

    def __str__(self):
        return self.message


class MKInternalError(MKHTTPException):
    status = 400


class MKMissingDataError(MKHTTPException):
    status = 400
