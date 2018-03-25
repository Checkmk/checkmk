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


import http

from cmk.exceptions import MKGeneralException, MKException


class RequestTimeout(MKException):
    """Is raised from the alarm signal handler (handle_request_timeout()) to
    abort page processing before the system apache times out."""
    pass



class FinalizeRequest(Exception):
    """Is used to end the HTTP request processing from deeper code levels"""
    # TODO: Drop this default and make exit code explicit for all call sites
    def __init__(self, code = None):
        super(FinalizeRequest, self).__init__(http.http_status(code))
        self.status = code or http.HTTP_OK



class HTTPRedirect(FinalizeRequest):
    """Is used to end the HTTP request processing from deeper code levels
    and making the client request another page after receiving the response."""
    def __init__(self, url, code=http.HTTP_MOVED_TEMPORARILY):
        super(HTTPRedirect, self).__init__(code)
        if code not in [ http.HTTP_MOVED_PERMANENTLY, http.HTTP_MOVED_TEMPORARILY ]:
            raise Exception("Invalid status code: %d" % code)

        self.url  = url



class MKAuthException(MKException):
    def __init__(self, reason):
        self.reason = reason
        super(MKAuthException, self).__init__(reason)


    def __str__(self):
        return self.reason


    def title(self):
        return _("Permission denied")


    def plain_title(self):
        return _("Authentication error")



class MKUnauthenticatedException(MKGeneralException):
    def title(self):
        return _("Not authenticated")


    def plain_title(self):
        return _("Missing authentication credentials")



class MKConfigError(MKException):
    def title(self):
        return _("Configuration error")


    def plain_title(self):
        return self.title()



class MKUserError(MKException):
    def __init__(self, varname, message):
        self.varname = varname
        self.message = message
        super(MKUserError, self).__init__(varname, message)


    def __str__(self):
        return self.message


    def title(self):
        return _("Invalid User Input")


    def plain_title(self):
        return _("User error")



class MKInternalError(MKException):
    pass
