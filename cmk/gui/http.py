#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper layer between WSGI and GUI application code"""

import sys
from typing import List, Optional, Any, Iterator, Union, Dict, Text, Tuple  # pylint: disable=unused-import
import six
import werkzeug.wrappers
import werkzeug.wrappers.json as json  # type: ignore[import]
from werkzeug.utils import get_content_type

from cmk.utils.encoding import ensure_unicode

from cmk.gui.globals import request
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError

UploadedFile = Tuple[str, str, bytes]


class LegacyVarsMixin(object):  # pylint: disable=useless-object-inheritance
    """Holds a dict of vars.

    These vars are being set throughout the codebase. Using this Mixin the vars will
    not modify the default request variables but rather shadow them. In the case of vars
    being removed, the variables from the request will show up again (given they were
    shadowed in the first place).
    """
    DELETED = object()

    def __init__(self, *args, **kw):
        # type: (*Any, **Any) -> None
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # [mypy:] Too many arguments for "__init__" of "object"  [call-arg]
        super(LegacyVarsMixin, self).__init__(*args, **kw)  # type: ignore[call-arg]
        self.legacy_vars = self._vars = {}  # type: Dict[str, Union[str, object]]

    def set_var(self, varname, value):
        # type: (str, Union[Text, str]) -> None
        if not isinstance(value, six.string_types):
            raise TypeError(_("Only str and unicode values are allowed, got %s") % type(value))

        # Py2: All items in self._vars are encoded at the moment. This should be changed one day,
        # but for the moment we treat vars set with set_var() equal to the vars received from the
        # HTTP request.
        varname = six.ensure_str(varname)
        value = six.ensure_str(value)

        self.legacy_vars[varname] = value

    def del_var(self, varname):
        # type: (Union[str, Text]) -> None
        varname = six.ensure_str(varname)
        self.legacy_vars[varname] = self.DELETED

    def del_vars(self, prefix=""):
        # type: (str) -> None
        for varname, _value in list(self.legacy_vars.items()):
            if varname.startswith(prefix):
                self.del_var(varname)

    def itervars(self, prefix=""):
        # type: (str) -> Iterator[Tuple[str, str]]
        skip = []
        for name, value in self.legacy_vars.items():
            if name.startswith(prefix):
                skip.append(name)
                if value is self.DELETED:
                    continue
                assert isinstance(value, str)
                yield name, value

        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        for name, val in super(LegacyVarsMixin, self).itervars(prefix=prefix):  # type: ignore[misc]
            if name in skip:
                continue
            yield name, val

    def has_var(self, varname):
        # type: (Union[str, Text]) -> bool
        varname = six.ensure_str(varname)
        if varname in self.legacy_vars:
            return self.legacy_vars[varname] is not self.DELETED

        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        return super(LegacyVarsMixin, self).has_var(varname)  # type: ignore[misc]

    def var(self, varname, default=None):
        # type: (str, Optional[str]) -> Optional[str]
        varname = six.ensure_str(varname)
        legacy_var = self.legacy_vars.get(varname, None)
        if legacy_var is not None:
            if legacy_var is not self.DELETED:
                assert isinstance(legacy_var, str)
                return legacy_var
            return default
        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        return super(LegacyVarsMixin, self).var(varname, default)  # type: ignore[misc]


class LegacyUploadMixin(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, *args, **kw):
        # type: (*Any, **Any) -> None
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # [mypy:] Too many arguments for "__init__" of "object"  [call-arg]
        super(LegacyUploadMixin, self).__init__(*args, **kw)  # type: ignore[call-arg]
        self.upload_cache = {}  # type: Dict[str, UploadedFile]

    def uploaded_file(self, name):
        # type: (str) -> UploadedFile
        # NOTE: There could be multiple entries with the same key, we ignore that for now...
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        f = self.files.get(name)  # type: ignore[attr-defined]
        if name not in self.upload_cache and f:
            self.upload_cache[name] = (f.filename, f.mimetype, f.read())
            f.close()

        try:
            upload = self.upload_cache[name]
        except KeyError:
            raise MKUserError(name, _("Please choose a file to upload."))

        return upload


class LegacyDeprecatedMixin(object):  # pylint: disable=useless-object-inheritance
    """Some wrappers which are still used while their use is considered deprecated.

    They are to be removed as they provide no additional value over the already available
    methods and properties in Request itself.
    """
    def itervars(self, prefix=""):
        # type: (str) -> Iterator[Tuple[str, Optional[str]]]
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        for name, values in self.values.lists():  # type: ignore[attr-defined]
            if name.startswith(prefix):
                # Preserve previous behaviour
                yield name, six.ensure_str(values[-1]) if values else None

    def var(self, name, default=None):
        # type: (str, Optional[str]) -> Optional[str]
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        values = self.values.getlist(name)  # type: ignore[attr-defined]
        if not values:
            return default

        # Preserve previous behaviour
        return six.ensure_str(values[-1])

    def has_var(self, varname):
        # type: (str) -> bool
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return varname in self.values  # type: ignore[attr-defined]

    def has_cookie(self, varname):
        # type: (str) -> bool
        """Whether or not the client provides a cookie with the given name"""
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return varname in self.cookies  # type: ignore[attr-defined]

    def cookie(self, varname, default=None):
        # type: (str, Optional[str]) -> Optional[str]
        """Return the value of the cookie provided by the client.

        If the cookie has not been set, None will be returned as a default.
        This default can be changed by passing is as the second parameter."""
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        value = self.cookies.get(varname, default)  # type: ignore[attr-defined]
        if value is not None:
            # Why would we want to do that? test_http.py requires it though.
            return six.ensure_str(value)
        return None

    def get_request_header(self, key, default=None):
        # type: (str, Optional[str]) -> Optional[str]
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.headers.get(key, default)  # type: ignore[attr-defined]

    def get_cookie_names(self):
        # type: () -> List[str]
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return list(self.cookies.keys())  # type: ignore[attr-defined]

    @property
    def referer(self):
        # type: () -> Optional[str]
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.referrer  # type: ignore[attr-defined]

    @property
    def request_method(self):
        # type: () -> str
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.method  # type: ignore[attr-defined]

    @property
    def requested_url(self):
        # type: () -> str
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.url  # type: ignore[attr-defined]

    @property
    def requested_file(self):
        # type: () -> str
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.base_url  # type: ignore[attr-defined]

    @property
    def is_ssl_request(self):
        # type: () -> bool
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.is_secure  # type: ignore[attr-defined]

    @property
    def remote_ip(self):
        # type: () -> str
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.remote_addr  # type: ignore[attr-defined]


class Request(LegacyVarsMixin, LegacyUploadMixin, LegacyDeprecatedMixin, json.JSONMixin,
              werkzeug.wrappers.Request):
    """Provides information about the users HTTP-request to the application

    This class essentially wraps the information provided with the WSGI environment
    and provides some low level functions to the application for accessing this information.
    These should be basic HTTP request handling things and no application specific mechanisms.
    """
    # pylint: disable=too-many-ancestors
    @property
    def request_timeout(self):
        # type: () -> int
        """The system web servers configured request timeout.

        This is the time before the request terminates from the view of the client."""
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
            val = self.var(varname, six.ensure_str(deflt) if deflt is not None else None)
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

        value = self.var(varname, "%d" % deflt if deflt is not None else None)
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

    def get_float_input(self, varname, deflt=None):
        # type: (str, Optional[float]) -> Optional[float]

        value = self.var(varname, "%s" % deflt if deflt is not None else None)
        if value is None:
            return None

        try:
            return float(value)
        except ValueError:
            raise MKUserError(varname, _("The parameter \"%s\" is not a float.") % varname)

    def get_float_input_mandatory(self, varname, deflt=None):
        # type: (str, Optional[float]) -> float
        value = self.get_float_input(varname, deflt)
        if value is None:
            raise MKUserError(varname, _("The parameter \"%s\" is missing.") % varname)
        return value


class Response(werkzeug.wrappers.Response):
    # NOTE: Currently we rely on a *relative* Location header in redirects!
    autocorrect_location_header = False

    def set_http_cookie(self, key, value, secure=None):
        # type: (str, str, Optional[bool]) -> None
        if secure is None:
            secure = request.is_secure
        super(Response, self).set_cookie(key, value, secure=secure, httponly=True)

    def set_content_type(self, mime_type):
        # type: (str) -> None
        self.headers["Content-type"] = get_content_type(mime_type, self.charset)
