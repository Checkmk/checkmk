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

import six
import werkzeug.wrappers
from werkzeug.utils import get_content_type

from cmk.gui.i18n import _


class LegacyVarsMixin(object):
    """Holds a dict of vars.

    These vars are being set throughout the codebase. Using this Mixin the vars will
    not modify the default request variables but rather shadow them. In the case of vars
    being removed, the variables from the request will show up again (given they were
    shadowed in the first place).
    """
    DELETED = object()

    def __init__(self, *args, **kw):
        super(LegacyVarsMixin, self).__init__(*args, **kw)
        self.legacy_vars = self._vars = {}

    def set_var(self, varname, value):
        if not isinstance(value, six.string_types):
            raise TypeError(_("Only str and unicode values are allowed, got %s") % type(value))

        # All items in self._vars are encoded at the moment. This should be changed one day,
        # but for the moment we treat vars set with set_var() equal to the vars received from
        # the HTTP request.
        if isinstance(varname, six.text_type):
            varname = varname.encode("utf-8")

        if isinstance(value, six.text_type):
            value = value.encode("utf-8")

        self.legacy_vars[varname] = value

    def del_var(self, varname):
        if isinstance(varname, six.text_type):
            varname = varname.encode("utf-8")
        self.legacy_vars[varname] = self.DELETED

    def del_vars(self, prefix=""):
        for varname, _value in list(self.legacy_vars.items()):
            if varname.startswith(prefix):
                self.del_var(varname)

    def itervars(self, prefix=""):
        skip = []
        for name, value in self.legacy_vars.items():
            if name.startswith(prefix):
                skip.append(name)
                if value is self.DELETED:
                    continue
                yield name, value

        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        for name, value in super(LegacyVarsMixin, self).itervars(prefix=prefix):
            if name in skip:
                continue
            yield name, value

    def has_var(self, varname):
        if isinstance(varname, six.text_type):
            varname = varname.encode("utf-8")
        if varname in self.legacy_vars:
            return self.legacy_vars[varname] is not self.DELETED

        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        return super(LegacyVarsMixin, self).has_var(varname)

    def var(self, varname, default=None):
        if isinstance(varname, six.text_type):
            varname = varname.encode("utf-8")

        legacy_var = self.legacy_vars.get(varname, None)
        if legacy_var is not None:
            if legacy_var is not self.DELETED:
                return legacy_var
            return default
        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        return super(LegacyVarsMixin, self).var(varname, default)


class LegacyUploadMixin(object):
    def __init__(self, *args, **kw):
        super(LegacyUploadMixin, self).__init__(*args, **kw)
        self.upload_cache = {}

    def uploaded_file(self, name):
        # NOTE: There could be multiple entries with the same key, we ignore that for now...
        f = self.files.get(name)
        if name not in self.upload_cache and f:
            self.upload_cache[name] = (f.filename, f.mimetype, f.read())
            f.close()

        return self.upload_cache[name]


class LegacyDeprecatedMixin(object):
    """Some wrappers which are still used while their use is considered deprecated.

    They are to be removed as they provide no additional value over the already available
    methods and properties in Request itself.
    """
    def itervars(self, prefix=""):
        # TODO: Deprecated
        for name, values in self.values.lists():
            if name.startswith(prefix):
                # Preserve previous behaviour
                yield name, values[-1].encode("utf-8") if values else None

    def var(self, name, default=None):
        # TODO: Deprecated
        values = self.values.getlist(name)
        if not values:
            return default

        # Preserve previous behaviour
        return values[-1].encode("utf-8")

    def has_var(self, varname):
        # TODO: Deprecated
        return varname in self.values

    def has_cookie(self, varname):
        """Whether or not the client provides a cookie with the given name"""
        # TODO: Deprecated
        return varname in self.cookies

    def cookie(self, varname, default=None):
        """Return the value of the cookie provided by the client.

        If the cookie has not been set, None will be returned as a default.
        This default can be changed by passing is as the second parameter."""
        # TODO: Deprecated
        value = self.cookies.get(varname, default)
        if value is not None:
            # Why would we want to do that? test_http.py requires it though.
            return value.encode('utf-8')

    def get_request_header(self, key, default=None):
        # TODO: Deprecated
        return self.headers.get(key, default)

    def get_cookie_names(self):
        # TODO: Deprecated
        return self.cookies.keys()

    @property
    def referer(self):
        # TODO: Deprecated
        return self.referrer

    @property
    def request_method(self):
        # TODO: Deprecated
        return self.method

    @property
    def requested_url(self):
        # TODO: Deprecated
        return self.url

    @property
    def requested_file(self):
        # TODO: Deprecated
        return self.base_url

    @property
    def is_ssl_request(self):
        # TODO: Deprecated
        return self.is_secure

    @property
    def remote_ip(self):
        # TODO: Deprecated
        return self.remote_addr


class Request(LegacyVarsMixin, LegacyUploadMixin, LegacyDeprecatedMixin, werkzeug.wrappers.Request):
    """Provides information about the users HTTP request to the application

    This class essentially wraps the information provided with the WSGI environment
    and provides some low level functions to the application for accessing these
    information. These should be basic HTTP request handling things and no application
    specific mechanisms.
    """
    # pylint: disable=too-many-ancestors
    @property
    def request_timeout(self):
        """The system web servers configured request timeout. This is the time
        before the request is terminated from the view of the client."""
        # TODO: Found no way to get this information from WSGI environment. Hard code
        #       the timeout for the moment.
        return 110


class Response(werkzeug.wrappers.Response):
    # NOTE: Currently we rely on a *relavtive* Location header in redirects!
    autocorrect_location_header = False

    def __init__(self, is_secure, *args, **kwargs):
        super(Response, self).__init__(*args, **kwargs)
        self._is_secure = is_secure

    def set_http_cookie(self, key, value, secure=None):
        if secure is None:
            # TODO: Use the request-self proxy for this so the callers don't have to supply this
            secure = self._is_secure
        super(Response, self).set_cookie(key, value, secure=secure, httponly=True)

    def set_content_type(self, mime_type):
        self.headers["Content-type"] = get_content_type(mime_type, self.charset)
