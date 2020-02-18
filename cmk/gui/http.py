#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper layer between WSGI and GUI application code"""

import sys
from typing import Optional, Text  # pylint: disable=unused-import
import six
import werkzeug.wrappers
import werkzeug.wrappers.json as json  # type: ignore[import]
from werkzeug.utils import get_content_type

from cmk.utils.encoding import ensure_unicode

from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError


class LegacyVarsMixin(object):  # pylint: disable=useless-object-inheritance
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

        # Py2: All items in self._vars are encoded at the moment. This should be changed one day,
        # but for the moment we treat vars set with set_var() equal to the vars received from the
        # HTTP request.
        varname = six.ensure_str(varname)
        value = six.ensure_str(value)

        self.legacy_vars[varname] = value

    def del_var(self, varname):
        varname = six.ensure_str(varname)
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
        varname = six.ensure_str(varname)
        if varname in self.legacy_vars:
            return self.legacy_vars[varname] is not self.DELETED

        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        return super(LegacyVarsMixin, self).has_var(varname)

    def var(self, varname, default=None):
        varname = six.ensure_str(varname)
        legacy_var = self.legacy_vars.get(varname, None)
        if legacy_var is not None:
            if legacy_var is not self.DELETED:
                return legacy_var
            return default
        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        return super(LegacyVarsMixin, self).var(varname, default)


class LegacyUploadMixin(object):  # pylint: disable=useless-object-inheritance
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


class LegacyDeprecatedMixin(object):  # pylint: disable=useless-object-inheritance
    """Some wrappers which are still used while their use is considered deprecated.

    They are to be removed as they provide no additional value over the already available
    methods and properties in Request itself.
    """
    def itervars(self, prefix=""):
        # TODO: Deprecated
        for name, values in self.values.lists():
            if name.startswith(prefix):
                # Preserve previous behaviour
                yield name, six.ensure_str(values[-1]) if values else None

    def var(self, name, default=None):
        # TODO: Deprecated
        values = self.values.getlist(name)
        if not values:
            return default

        # Preserve previous behaviour
        return six.ensure_str(values[-1])

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
            return six.ensure_str(value)

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


class Request(LegacyVarsMixin, LegacyUploadMixin, LegacyDeprecatedMixin, json.JSONMixin,
              werkzeug.wrappers.Request):
    """Provides information about the users HTTP-request to the application

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

    # TODO: For historic reasons this needs to return byte strings. We will clean this up
    # soon when moving to python 3
    def get_str_input(self, varname, deflt=None):
        # type: (str, Optional[str]) -> Optional[str]
        return self.var(varname, deflt)

    def get_str_input_mandatory(self, varname, deflt=None):
        # type: (str, Optional[str]) -> str
        value = self.var(varname, deflt)
        if value is None:
            raise MKUserError(varname, _("The parameter \"%s\" is missing.") % varname)
        return value

    # TODO: For historic reasons this needs to return byte strings. We will clean this up
    # soon when moving to python 3
    def get_ascii_input(self, varname, deflt=None):
        # type: (str, Optional[str]) -> Optional[str]
        """Helper to retrieve a byte string and ensure it only contains ASCII characters
        In case a non ASCII character is found an MKUserError() is raised."""
        value = self.var(varname, deflt)

        if value is None:
            return value

        if sys.version_info[0] >= 3:
            if not value.isascii():
                raise MKUserError(varname, _("The given text must only contain ASCII characters."))
        else:
            try:
                value.decode("ascii")
            except UnicodeDecodeError:
                raise MKUserError(varname, _("The given text must only contain ASCII characters."))

        return value

    # TODO: For historic reasons this needs to return byte strings. We will clean this up
    # soon when moving to python 3
    def get_ascii_input_mandatory(self, varname, deflt=None):
        # type: (str, Optional[str]) -> str
        value = self.get_ascii_input(varname, deflt)
        if value is None:
            raise MKUserError(varname, _("The parameter \"%s\" is missing.") % varname)
        return value

    def get_unicode_input(self, varname, deflt=None):
        # type: (str, Optional[Text]) -> Optional[Text]
        try:
            val = self.var(varname, deflt)
            if val is None:
                return None
            return ensure_unicode(val)
        except UnicodeDecodeError:
            raise MKUserError(
                varname,
                _("The given text is wrong encoded. "
                  "You need to provide a UTF-8 encoded text."))

    def get_unicode_input_mandatory(self, varname, deflt=None):
        # type: (str, Optional[Text]) -> Text
        value = self.get_unicode_input(varname, deflt)
        if value is None:
            raise MKUserError(varname, _("The parameter \"%s\" is missing.") % varname)
        return value

    def get_integer_input(self, varname, deflt=None):
        # type: (str, Optional[int]) -> Optional[int]

        value = self.var(varname, deflt)
        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            raise MKUserError(varname, _("The parameter \"%s\" is not an integer.") % varname)

    def get_integer_input_mandatory(self, varname, deflt=None):
        # type: (str, Optional[int]) -> int
        value = self.get_integer_input(varname, deflt)
        if value is None:
            raise MKUserError(varname, _("The parameter \"%s\" is missing.") % varname)
        return value


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
