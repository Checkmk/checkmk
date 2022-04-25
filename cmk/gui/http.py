#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper layer between WSGI and GUI application code"""

import ast
import json
import urllib.parse
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple, TypeVar, Union

import werkzeug
from six import ensure_str
from werkzeug.utils import get_content_type

import cmk.gui.utils as utils
from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.i18n import _

UploadedFile = Tuple[str, str, bytes]
T = TypeVar("T")
Value = TypeVar("Value")


class LegacyVarsMixin:
    """Holds a dict of vars.

    These vars are being set throughout the codebase. Using this Mixin the vars will
    not modify the default request variables but rather shadow them. In the case of vars
    being removed, the variables from the request will show up again (given they were
    shadowed in the first place).
    """

    DELETED = object()

    def __init__(self, *args: Any, **kw: Any) -> None:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # [mypy:] Too many arguments for "__init__" of "object"  [call-arg]
        super().__init__(*args, **kw)  # type: ignore[call-arg]
        self.legacy_vars = self._vars = {}  # type: Dict[str, Union[str, object]]

    def set_var(self, varname: str, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(_("Only str and unicode values are allowed, got %s") % type(value))

        self.legacy_vars[varname] = value

    def del_var(self, varname: str) -> None:
        self.legacy_vars[varname] = self.DELETED

    def del_vars(self, prefix: str = "") -> None:
        for varname, _value in self.itervars(prefix):
            if varname.startswith(prefix):
                self.del_var(varname)

    def itervars(self, prefix: str = "") -> Iterator[Tuple[str, str]]:
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
        for name, val in super().itervars(prefix=prefix):  # type: ignore[misc]
            if name in skip:
                continue
            yield name, val

    def has_var(self, varname: str) -> bool:
        if varname in self.legacy_vars:
            return self.legacy_vars[varname] is not self.DELETED

        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        return super().has_var(varname)  # type: ignore[misc]

    def var(self, varname: str, default: Optional[str] = None) -> Optional[str]:
        legacy_var = self.legacy_vars.get(varname, None)
        if legacy_var is not None:
            if legacy_var is not self.DELETED:
                assert isinstance(legacy_var, str)
                return legacy_var
            return default
        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        return super().var(varname, default)  # type: ignore[misc]


class LegacyUploadMixin:
    def __init__(self, *args: Any, **kw: Any) -> None:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # [mypy:] Too many arguments for "__init__" of "object"  [call-arg]
        super().__init__(*args, **kw)  # type: ignore[call-arg]
        self.upload_cache: Dict[str, UploadedFile] = {}

    def uploaded_file(self, name: str) -> UploadedFile:
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


class LegacyDeprecatedMixin:
    """Some wrappers which are still used while their use is considered deprecated.

    They are to be removed as they provide no additional value over the already available
    methods and properties in Request itself.
    """

    def itervars(self, prefix: str = "") -> Iterator[Tuple[str, Optional[str]]]:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        # ? type of values attribute and functions defined with it are unclear
        for name, values in self.values.lists():  # type: ignore[attr-defined]
            if name.startswith(prefix):
                # Preserve previous behaviour
                yield name, ensure_str(  # pylint: disable= six-ensure-str-bin-call
                    values[-1]
                ) if values else None

    def var(self, name: str, default: Optional[str] = None) -> Optional[str]:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        values = self.values.getlist(name)  # type: ignore[attr-defined]
        if not values:
            return default

        # Preserve previous behaviour
        return ensure_str(values[-1])  # pylint: disable= six-ensure-str-bin-call

    def has_var(self, varname: str) -> bool:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return varname in self.values  # type: ignore[attr-defined]

    def has_cookie(self, varname: str) -> bool:
        """Whether or not the client provides a cookie with the given name"""
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return varname in self.cookies  # type: ignore[attr-defined]

    def cookie(self, varname: str, default: Optional[str] = None) -> Optional[str]:
        """Return the value of the cookie provided by the client.

        If the cookie has not been set, None will be returned as a default.
        This default can be changed by passing is as the second parameter."""
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        # ? type of self.cookies argument is unclear
        value = self.cookies.get(varname, default)  # type: ignore[attr-defined]
        if value is not None:
            # Why would we want to do that? test_http.py requires it though.
            return ensure_str(value)  # pylint: disable= six-ensure-str-bin-call
        return None

    def get_request_header(self, key: str, default: Optional[str] = None) -> Optional[str]:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.headers.get(key, default)  # type: ignore[attr-defined]

    @property
    def referer(self) -> Optional[str]:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.referrer  # type: ignore[attr-defined]

    @property
    def request_method(self) -> str:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.method  # type: ignore[attr-defined]

    @property
    def requested_url(self) -> str:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.url  # type: ignore[attr-defined]

    @property
    def requested_file(self) -> str:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.base_url  # type: ignore[attr-defined]

    @property
    def is_ssl_request(self) -> bool:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.is_secure  # type: ignore[attr-defined]


def mandatory_parameter(varname: str, value: Optional[T]) -> T:
    if value is None:
        raise MKUserError(varname, _('The parameter "%s" is missing.') % varname)
    return value


class Request(
    LegacyVarsMixin,
    LegacyUploadMixin,
    LegacyDeprecatedMixin,
    werkzeug.Request,
):
    """Provides information about the users HTTP-request to the application

    This class essentially wraps the information provided with the WSGI environment
    and provides some low level functions to the application for accessing this information.
    These should be basic HTTP request handling things and no application specific mechanisms.
    """

    # pylint: disable=too-many-ancestors

    def __init__(self, environ, populate_request=True, shallow=False):
        super().__init__(environ, populate_request=populate_request, shallow=shallow)
        self._verify_not_using_threaded_mpm()

    def _verify_not_using_threaded_mpm(self) -> None:
        if self.is_multithread:
            raise MKGeneralException(
                _(
                    "You are trying to Checkmk together with a threaded Apache multiprocessing module (MPM). "
                    "Check_MK is only working with the prefork module. Please change the MPM module to make "
                    "Check_MK work."
                )
            )

    @property
    def request_timeout(self) -> int:
        """The system web servers configured request timeout.

        This is the time before the request terminates from the view of the client."""
        # TODO: Found no way to get this information from WSGI environment. Hard code
        #       the timeout for the moment.
        return 110

    @property
    def remote_ip(self) -> Optional[str]:
        """Selects remote addr from the given list of ips in
        X-Forwarded-For. Picks first non-trusted ip address.
        """
        trusted_proxies: List[str] = ["127.0.0.1", "::1"]
        remote_addr: Optional[str] = self.remote_addr
        forwarded_for = self.environ.get("HTTP_X_FORWARDED_FOR", "").split(",")
        if remote_addr in trusted_proxies:
            return next(
                (
                    ip
                    for ip in reversed([x for x in [x.strip() for x in forwarded_for] if x])
                    if ip not in trusted_proxies
                ),
                remote_addr,
            )
        return self.remote_addr

    def get_str_input(self, varname: str, deflt: Optional[str] = None) -> Optional[str]:
        return self.var(varname, deflt)

    def get_str_input_mandatory(self, varname: str, deflt: Optional[str] = None) -> str:
        return mandatory_parameter(varname, self.get_str_input(varname, deflt))

    def get_ascii_input(self, varname: str, deflt: Optional[str] = None) -> Optional[str]:
        """Helper to retrieve a byte string and ensure it only contains ASCII characters
        In case a non ASCII character is found an MKUserError() is raised."""
        value = self.get_str_input(varname, deflt)
        if value is None:
            return value
        if not value.isascii():
            raise MKUserError(varname, _("The given text must only contain ASCII characters."))
        return value

    def get_ascii_input_mandatory(self, varname: str, deflt: Optional[str] = None) -> str:
        return mandatory_parameter(varname, self.get_ascii_input(varname, deflt))

    def get_binary_input(self, varname: str, deflt: Optional[bytes] = None) -> Optional[bytes]:
        val = self.var(varname, deflt.decode() if deflt is not None else None)
        if val is None:
            return None
        return val.encode()

    def get_binary_input_mandatory(self, varname: str, deflt: Optional[bytes] = None) -> bytes:
        return mandatory_parameter(varname, self.get_binary_input(varname, deflt))

    def get_integer_input(self, varname: str, deflt: Optional[int] = None) -> Optional[int]:

        value = self.var(varname, "%d" % deflt if deflt is not None else None)
        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            raise MKUserError(varname, _('The parameter "%s" is not an integer.') % varname)

    def get_integer_input_mandatory(self, varname: str, deflt: Optional[int] = None) -> int:
        return mandatory_parameter(varname, self.get_integer_input(varname, deflt))

    def get_float_input(self, varname: str, deflt: Optional[float] = None) -> Optional[float]:

        value = self.var(varname, "%s" % deflt if deflt is not None else None)
        if value is None:
            return None

        try:
            return float(value)
        except ValueError:
            raise MKUserError(varname, _('The parameter "%s" is not a float.') % varname)

    def get_float_input_mandatory(self, varname: str, deflt: Optional[float] = None) -> float:
        return mandatory_parameter(varname, self.get_float_input(varname, deflt))

    def get_item_input(self, varname: str, collection: Mapping[str, Value]) -> Tuple[Value, str]:
        """Helper to get an item from the given collection
        Raises a MKUserError() in case the requested item is not available."""
        item = self.get_ascii_input(varname)
        if item not in collection:
            raise MKUserError(varname, _("The requested item %s does not exist") % item)
        assert item is not None
        return collection[item], item

    # TODO: Invalid default URL is not validated. Should we do it?
    # TODO: This is only protecting against some not allowed URLs but does not
    #       really verify that this is some kind of URL.
    def get_url_input(self, varname: str, deflt: Optional[str] = None) -> str:
        """Helper function to retrieve a URL from HTTP parameters

        This is mostly used to the "back url" which can then be used to create
        a link to the previous page. For this kind of functionality it is
        necessary to restrict the URLs to prevent different attacks on users.

        In case the parameter is not given or is not valid the deflt URL will
        be used. In case no deflt URL is given a MKUserError() is raised.
        """
        if not self.has_var(varname):
            if deflt is not None:
                return deflt
            raise MKUserError(varname, _('The parameter "%s" is missing.') % varname)

        url = self.var(varname)
        assert url is not None

        if not utils.is_allowed_url(url):
            if deflt:
                return deflt
            raise MKUserError(varname, _('The parameter "%s" is not a valid URL.') % varname)

        return url

    @contextmanager
    def stashed_vars(self) -> Iterator[None]:
        """Remember current request variables and restore original state when leaving the context"""
        saved_vars = dict(self.itervars())
        try:
            yield
        finally:
            self.del_vars()
            for varname, value in saved_vars.items():
                self.set_var(varname, value)

    # HACKY WORKAROUND, REMOVE WHEN NO LONGER NEEDED
    def del_var_from_env(self, varname: str) -> None:
        """Remove HTTP request variables from the environment

        We need to get rid of query-string entries which can contain secret information.
        As this is the only location where these are stored on the WSGI environment this
        should be enough.

        See also cmk.gui.globals:RequestContext
        """
        # Filter the variables even if there are multiple copies of them (this is allowed).
        decoded_qs = [(key, value) for key, value in self.args.items(multi=True) if key != varname]
        self.query_string = urllib.parse.urlencode(decoded_qs).encode("utf-8")
        self.environ["QUERY_STRING"] = self.query_string
        # We remove the form entry. As this entity is never copied it will be modified within
        # its cache.
        try:
            dict.pop(self.form, varname)
        except KeyError:
            pass
        # We remove the __dict__ entries to allow @cached_property to reload them from
        # the environment. The rest of the request object stays the same.
        self.__dict__.pop("args", None)
        self.__dict__.pop("values", None)

    # TODO: The mixture of request variables and json request argument is a nasty hack. Split this
    # up into explicit methods that either use the one or the other method, remove the call sites to
    # this method and then this method.
    def get_request(self, exclude_vars: Optional[List[str]] = None) -> Dict[str, Any]:
        """Returns a dictionary containing all parameters the user handed over to this request.

        The concept is that the user can either provide the data in a single "request" variable,
        which contains the request data encoded as JSON, or provide multiple GET/POST vars which
        are then used as top level entries in the request object.
        """

        if exclude_vars is None:
            exclude_vars = []

        if self.var("request_format") == "python":
            python_request = self.var("request", "{}")
            assert python_request is not None
            try:
                request_ = ast.literal_eval(python_request)
            except (SyntaxError, ValueError) as e:
                raise MKUserError(
                    "request", _("Failed to parse Python request: '%s': %s") % (python_request, e)
                )
        else:
            json_request = self.var("request", "{}")
            assert json_request is not None
            try:
                request_ = json.loads(json_request)
                request_["request_format"] = "json"
            except ValueError as e:  # Python3: json.JSONDecodeError
                raise MKUserError(
                    "request", _("Failed to parse JSON request: '%s': %s") % (json_request, e)
                )

        for key, val in self.itervars():
            if key not in ["request", "output_format"] + exclude_vars:
                request_[key] = val

        return request_


class Response(werkzeug.Response):
    # NOTE: Currently we rely on a *relative* Location header in redirects!
    autocorrect_location_header = False

    default_mimetype = "text/html"

    def set_http_cookie(self, key: str, value: str, *, secure: bool) -> None:
        super().set_cookie(key, value, secure=secure, httponly=True, samesite="Lax")

    def set_content_type(self, mime_type: str) -> None:
        self.headers["Content-type"] = get_content_type(mime_type, self.charset)


# From request context
request: Request = request_local_attr("request")
response: Response = request_local_attr("response")
