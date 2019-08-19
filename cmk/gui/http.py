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
"""Wrapper layer between WSGI and the GUI application code"""

import re

import six
import werkzeug.http
import werkzeug.wrappers

import cmk.gui.log as log
from cmk.gui.i18n import _

# TODO: For some aracane reason, we are a bit restrictive about the allowed
# variable names. Try to figure out why...
_VARNAME_REGEX = re.compile(r'^[:\w.%*+=-]+$')


def _valid_varname(v):
    return _VARNAME_REGEX.match(v)


class Request(object):
    """Provides information about the users HTTP request to the application

    This class essentially wraps the information provided with the WSGI environment
    and provides some low level functions to the application for accessing these
    information. These should be basic HTTP request handling things and no application
    specific mechanisms."""
    def __init__(self, wsgi_environ):
        super(Request, self).__init__()
        self._logger = log.logger.getChild("http.Request")
        self._wsgi_environ = wsgi_environ

        # Last occurrence takes precedence, making appending to current URL simpler
        wrequest = werkzeug.wrappers.Request(wsgi_environ)
        self._vars = {k: vs[-1].encode("utf-8") \
                      for k, vs in wrequest.values.lists()
                      if _valid_varname(k)}

        # NOTE: There could be multiple entries with the same key, we ignore that for now...
        self._uploads = {}
        for k, f in wrequest.files.iteritems():
            # TODO: We read the whole data here and remember it. Should we
            # offer the underlying stream directly?
            self._uploads[k] = (f.filename, f.mimetype, f.read())
            f.close()

        # TODO: To be compatible with Check_MK <1.5 handling / code base we
        # prevent parse_cookie() from decoding the stuff to unicode. One bright
        # day we'll switch all input stuff to be parsed to unicode, then we'll
        # clean this up!
        self.cookies = werkzeug.http.parse_cookie(wsgi_environ, charset=None)

    @property
    def requested_file(self):
        return self._wsgi_environ["SCRIPT_NAME"]

    @property
    def requested_url(self):
        return self._wsgi_environ["REQUEST_URI"]

    @property
    def request_method(self):
        return self._wsgi_environ['REQUEST_METHOD']

    @property
    def remote_ip(self):
        try:
            return self._wsgi_environ["HTTP_X_FORWARDED_FOR"].split(",")[-1].strip()
        except KeyError:
            return self._wsgi_environ["REMOTE_ADDR"]

    @property
    def remote_user(self):
        """Returns either the REMOTE_USER authenticated with the web server or None"""
        return self._wsgi_environ.get("REMOTE_USER")

    @property
    def is_ssl_request(self):
        return self._wsgi_environ.get("HTTP_X_FORWARDED_PROTO") == "https"

    @property
    def is_multithreaded(self):
        return self._wsgi_environ.get("wsgi.multithread", False)

    @property
    def user_agent(self):
        return self._wsgi_environ.get("USER_AGENT", "")

    @property
    def referer(self):
        return self._wsgi_environ.get("REFERER")

    @property
    def request_timeout(self):
        """The system web servers configured request timeout. This is the time
        before the request is terminated from the view of the client."""
        # TODO: Found no way to get this information from WSGI environment. Hard code
        # the timeout for the moment.
        return 110

    def get_request_header(self, key, deflt=None):
        """Returns the value of a HTTP request header

        Applies the CGI variable name mangling to the requested variable name
        which is used by Apache 2.4+ and mod_wsgi to finally produce the
        wsgi_environ.

        a) mod_wsgi/Apache only make the variables available that consist of alpha numeric
           and minus characters. Other variables are skipped.
        b) e.g. X-Remote-User is available as HTTP_X_REMOTE_USER
        """
        env_key = "HTTP_%s" % key.upper().replace("-", "_")
        return self._wsgi_environ.get(env_key, deflt)

    def has_cookie(self, varname):
        """Whether or not the client provides a cookie with the given name"""
        return varname in self.cookies

    def get_cookie_names(self):
        """Return the names of all cookies sent by the client"""
        return self.cookies.keys()

    def cookie(self, varname, deflt=None):
        """Return either the value of the cookie provided by the client, the given deflt value or None"""
        try:
            return self.cookies[varname]
        except:
            return deflt

    #
    # Variable handling
    #

    def var(self, varname, deflt=None):
        return self._vars.get(varname, deflt)

    def has_var(self, varname):
        return varname in self._vars

    def itervars(self, prefix=""):
        return (item \
                for item in self._vars.iteritems() \
                if item[0].startswith(prefix))

    # TODO: self._vars should be strictly read only in the Request() object
    def set_var(self, varname, value):
        if not isinstance(value, six.string_types):
            raise TypeError(_("Only str and unicode values are allowed, got %s") % type(value))

        # All items in self._vars are encoded at the moment. This should be changed one day,
        # but for the moment we treat vars set with set_var() equal to the vars received from
        # the HTTP request.
        if isinstance(varname, unicode):
            varname = varname.encode("utf-8")
        if isinstance(value, unicode):
            value = value.encode("utf-8")

        self._vars[varname] = value

    # TODO: self._vars should be strictly read only in the Request() object
    def del_var(self, varname):
        self._vars.pop(varname, None)

    # TODO: self._vars should be strictly read only in the Request() object
    def del_vars(self, prefix=""):
        for varname, _value in list(self.itervars(prefix)):
            self.del_var(varname)

    def uploaded_file(self, varname):
        return self._uploads.get(varname)


class Response(werkzeug.wrappers.Response):
    # NOTE: Currently we rely on a *relavtive* Location header in redirects!
    autocorrect_location_header = False

    def __init__(self, is_secure, *args, **kwargs):
        super(Response, self).__init__(*args, **kwargs)
        self._is_secure = is_secure

    def set_http_cookie(self, key, value, secure=None):
        if secure is None:
            secure = self._is_secure
        super(Response, self).set_cookie(key, value, secure=secure, httponly=True)
