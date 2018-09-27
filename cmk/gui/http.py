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
import time
import werkzeug.http
import cgi

import cmk.gui.log as log
from cmk.gui.i18n import _
from cmk.gui.globals import html
import cmk.gui.http_status
from cmk.gui.exceptions import HTTPRedirect

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

        # Structures filled using the request environment
        self.vars     = {}
        self.listvars = {} # for variables with more than one occurrence
        self.uploads  = {}
        # TODO: To be compatible with Check_MK <1.5 handling / code base we
        # prevent parse_cookie() from decoding the stuff to unicode. One bright
        # day we'll switch all input stuff to be parsed to unicode, then we'll
        # clean this up!
        self.cookies  = werkzeug.http.parse_cookie(wsgi_environ, charset=None)

        self._init_vars(wsgi_environ)


    def _init_vars(self, wsgi_environ):
        wsgi_input = wsgi_environ["wsgi.input"]
        if not wsgi_input:
            return

        fields = None
        try:
            fields = cgi.FieldStorage(wsgi_input, None, "", wsgi_environ,
                                    keep_blank_values=1)
        except MemoryError:
            raise Exception('The maximum request size has been exceeded.')

        self._init_vars_from_field_storage(fields)


    def _init_vars_from_field_storage(self, fields):
        # TODO: Previously the regex below matched any alphanumeric character plus any character
        # from set(r'%*+,-./:;<=>?@[\_'), but this was very probably unintended. Now we only allow
        # alphanumeric characters plus any character from set('%*+-._'), which is probably still a
        # bit too broad. We should really figure out what we need and make sure that we only use
        # that restricted set.
        varname_regex = re.compile(r'^[\w.%*+-]+$')

        for field in fields.list:
            varname = field.name

            # To prevent variours injections, we only allow a defined set
            # of characters to be used in variables
            if not varname_regex.match(varname):
                continue

            # put uploaded file infos into separate storage
            if field.filename is not None:
                self.uploads[varname] = (field.filename, field.type, field.value)

            else: # normal variable
                # Multiple occurrance of a variable? Store in extra list dict
                if varname in self.vars:
                    if varname in self.listvars:
                        self.listvars[varname].append(field.value)
                    else:
                        self.listvars[varname] = [ self.vars[varname], field.value ]
                # In the single-value-store the last occurrance of a variable
                # has precedence. That makes appending variables to the current
                # URL simpler.
                self.vars[varname] = field.value


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
        return self._wsgi_environ.get(key, deflt)


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

    def var(self, varname, deflt = None):
        return self.vars.get(varname, deflt)


    def has_var(self, varname):
        return varname in self.vars


    def has_var_prefix(self, prefix):
        """Checks if a variable with a given prefix is present"""
        return any(var.startswith(prefix) for var in self.vars)


    def var_utf8(self, varname, deflt = None):
        val = self.vars.get(varname, deflt)
        if type(val) == str:
            return val.decode("utf-8")
        return val


    def all_vars(self):
        return self.vars


    def all_varnames_with_prefix(self, prefix):
        for varname in self.vars:
            if varname.startswith(prefix):
                yield varname


    # Return all values of a variable that possible occurs more
    # than once in the URL. note: self.listvars does contain those
    # variable only, if the really occur more than once.
    def list_var(self, varname):
        if varname in self.listvars:
            return self.listvars[varname]
        elif varname in self.vars:
            return [self.vars[varname]]
        return []


    # Adds a variable to listvars and also set it
    def add_var(self, varname, value):
        self.listvars.setdefault(varname, [])
        self.listvars[varname].append(value)
        self.vars[varname] = value


    # TODO: self.vars should be strictly read only in the Request() object
    def set_var(self, varname, value):
        if value is None:
            self.del_var(varname)

        elif type(value) in [ str, unicode ]:
            self.vars[varname] = value

        else:
            # crash report please
            raise TypeError(_("Only str and unicode values are allowed, got %s") % type(value))


    # TODO: self.vars should be strictly read only in the Request() object
    def del_var(self, varname):
        self.vars.pop(varname, None)
        self.listvars.pop(varname, None)


    # TODO: self.vars should be strictly read only in the Request() object
    def del_all_vars(self, prefix = None):
        if not prefix:
            self.vars = {}
            self.listvars = {}
        else:
            self.vars = dict(p for p in self.vars.iteritems()
                             if not p[0].startswith(prefix))
            self.listvars = dict(p for p in self.listvars.iteritems()
                                 if not p[0].startswith(prefix))


    def uploaded_file(self, varname, default = None):
        return self.uploads.get(varname, default)



class Response(object):
    """HTTP response handling

    The application uses this class to produce a HTTP response which is then handed
    over to the WSGI server for sending the response to the client.
    """

    def __init__(self, request):
        super(Response, self).__init__()
        self._logger = log.logger.getChild("http.Response")

        self._request = request

        self._status_code = cmk.gui.http_status.HTTP_OK
        self._output = []
        self._headers_out = []


    def set_status_code(self, code):
        """Set the HTTP status code of the response to the given code"""
        self._status_code = code


    def set_content_type(self, ty):
        """Set the content type of the response to the given type"""
        self.set_http_header("Content-type", ty)


    def set_http_header(self, key, val, prevent_duplicate=True):
        """Set a HTTP header to send to the client with the response.

        By default this function ensures that no header is set twice. For some headers, like e.g.
        cookies it makes sense to set the headers multiple times. Set prevent_duplicate=False to
        get this behaviour."""
        if prevent_duplicate:
            for this_key, this_val in self._headers_out[:]:
                if this_key == key:
                    self._headers_out.remove((this_key, this_val))

        self._headers_out.append((key, val))


    def set_cookie(self, varname, value, expires=None):
        """Send the given cookie to the client with the response"""
        if expires is not None:
            assert type(expires) == int

        cookie_header = werkzeug.http.dump_cookie(
            varname,
            value,
            # Use cookie for all URLs of the host (to make cross site use possible)
            path="/",
            # Tell client not to use the cookie within javascript
            httponly=True,
            # Tell client to only use the cookie for SSL connections
            secure=self._request.is_ssl_request,
            expires=expires,
        )

        self.set_http_header("Set-Cookie", cookie_header, prevent_duplicate=False)


    def del_cookie(self, varname):
        """Tell the client to invalidate cookies with the given varname"""
        self.set_cookie(varname, '', expires=-60)


    def http_redirect(self, url):
        """Finalize the currently processed page with a HTTP redirect to the given URL"""
        raise HTTPRedirect(url)


    def write(self, text):
        """Extend the response body with the given text"""
        self._output.append(text)


    @property
    def http_status(self):
        """Provides the HTTP response status header (code incl. text)"""
        return cmk.gui.http_status.status_with_reason(self._status_code)


    @property
    def headers(self):
        """Provides the HTTP response headers to be sent to the client"""
        return self._headers_out


    def flush_output(self):
        """Get response body iterable for the response

        The output is handed over as list with a single byte string
        as recommended by PEP 3333."""
        output, self._output = self._output, []
        return [ "".join(output) ]
