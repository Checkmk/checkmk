#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005
# mypy: disable-error-code="no-any-return"

"""Wrapper layer between WSGI and GUI application code"""

import ast
import json
import time
import urllib.parse
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from enum import auto, StrEnum
from typing import Any, cast, Literal, overload, Protocol, TypeVar

import flask
from flask import request as flask_request
from pydantic import BaseModel
from werkzeug.utils import get_content_type

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import url_prefix

from cmk.utils.urls import is_allowed_url

from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _

UploadedFile = tuple[str, str, bytes]
T = TypeVar("T")
Value = TypeVar("Value")

HTTPMethod = Literal["get", "put", "post", "delete"]


class ContentDispositionType(StrEnum):
    """
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition

    Form data currently not supported by us.
    """

    INLINE = auto()
    ATTACHMENT = auto()


# This is used to match content-type to file ending (file extension) in
# set_content_disposition. Feel free to add more extensions and content-types.
# However please make sure that the added types are precise as we are
# restricting types mitigate risk.
FILE_EXTENSIONS = {
    "application/javascript": [".js"],
    "application/json": [".json"],
    "application/pdf": [".pdf"],
    "application/x-deb": [".deb"],
    "application/x-rpm": [".rpm"],
    "application/x-pkg": [".pkg"],
    "application/x-tgz": [".tar.gz"],
    "application/x-msi": [".msi"],
    "application/x-mkp": [".mkp"],
    "image/png": [".png"],
    "text/csv": [".csv"],
    "text/plain": [".txt"],
    "application/x-pem-file": [".pem"],
}


class ValidatedClass(Protocol):
    """Classes like int, UserId, etc..."""

    def __new__(cls, value: str) -> "ValidatedClass":
        # must raise ValueErrors if value is not valid
        ...


Validation_T = TypeVar("Validation_T", bound=ValidatedClass)

Model_T = TypeVar("Model_T", bound=BaseModel)


class LegacyVarsMixin:
    """Holds a dict of vars.

    These vars are being set throughout the codebase. Using this Mixin the vars will
    not modify the default request variables but rather shadow them. In the case of vars
    being removed, the variables from the request will show up again (given they were
    shadowed in the first place).
    """

    DELETED = object()

    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self._vars: dict[str, str | object] = {}
        self.legacy_vars = self._vars

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

    def itervars(self, prefix: str = "") -> Iterator[tuple[str, str]]:
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

    @overload
    def var(self, name: str) -> str | None: ...

    @overload
    def var(self, name: str, default: str) -> str: ...

    @overload
    def var(self, name: str, default: str | None) -> str | None: ...

    def var(self, name: str, default: str | None = None) -> str | None:
        legacy_var = self.legacy_vars.get(name, None)
        if legacy_var is not None:
            if legacy_var is not self.DELETED:
                assert isinstance(legacy_var, str)
                return legacy_var
            return default
        # We only fall through to the real HTTP request if our var isn't set and isn't deleted.
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        return super().var(name, default)  # type: ignore[misc]


class LegacyUploadMixin:
    def __init__(self, *args: Any, **kw: Any) -> None:
        super().__init__(*args, **kw)
        self.upload_cache: dict[str, UploadedFile] = {}

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

    def itervars(self, prefix: str = "") -> Iterator[tuple[str, str | None]]:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        for name, values in self.values.lists():  # type: ignore[attr-defined]
            if name.startswith(prefix):
                # Preserve previous behaviour
                yield (name, (values[-1] if values else None))

    @overload
    def var(self, name: str) -> str | None: ...

    @overload
    def var(self, name: str, default: str) -> str: ...

    @overload
    def var(self, name: str, default: str | None) -> str | None: ...

    def var(self, name: str, default: str | None = None) -> str | None:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        values = self.values.getlist(name)  # type: ignore[attr-defined]
        if not values:
            return default

        # Preserve previous behaviour
        return str(values[-1])

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

    def cookie(self, varname: str, default: str | None = None) -> str | None:
        """Return the value of the cookie provided by the client.

        If the cookie has not been set, None will be returned as a default.
        This default can be changed by passing is as the second parameter."""
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        value = self.cookies.get(varname, default)  # type: ignore[attr-defined]
        if value is not None:
            return value
        return None

    def get_request_header(self, key: str, default: str | None = None) -> str | None:
        # TODO: mypy does not know about the related mixin classes. This whole class can be cleaned
        # up with 1.7, once we have moved to python 3.
        # TODO: Deprecated
        return self.headers.get(key, default)  # type: ignore[attr-defined]

    @property
    def referer(self) -> str | None:
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


def mandatory_parameter(varname: str, value: T | None) -> T:
    if value is None:
        raise MKUserError(varname, _('The parameter "%s" is missing.') % varname)
    return value


class Request(
    LegacyVarsMixin,
    LegacyUploadMixin,
    LegacyDeprecatedMixin,
    flask.Request,
):
    """Provides information about the users HTTP-request to the application

    This class essentially wraps the information provided with the WSGI environment
    and provides some low-level functions to the application for accessing this information.
    These should be basic HTTP request handling things and no application specific mechanisms.
    """

    # The system web servers configured request timeout.
    # This is the time before the request terminates from the view of the client.
    request_timeout = 110

    # TODO investigate why there are so many form_parts
    max_form_parts = 20000
    max_form_memory_size = 20 * 1024 * 1024
    meta: dict[str, Any]

    def __init__(self, environ: dict, populate_request: bool = True, shallow: bool = False) -> None:
        # Modify the environment to fix double URLs in some apache configurations, only once.
        if "apache.version" in environ and environ.get("SCRIPT_NAME"):
            environ["PATH_INFO"] = environ["SCRIPT_NAME"]
            del environ["SCRIPT_NAME"]

        super().__init__(environ, populate_request=populate_request, shallow=shallow)
        self.started = time.monotonic()
        self.meta = {}
        self._verify_not_using_threaded_mpm()

    def _verify_not_using_threaded_mpm(self) -> None:
        if self.is_multithread:
            raise MKGeneralException(
                _(
                    "You are trying to use Checkmk together with a threaded "
                    "Apache multiprocessing module (MPM). Checkmk is only "
                    "working with the prefork module. Please change the MPM "
                    "module to make Checkmk work."
                )
            )

    @property
    def remote_ip(self) -> str | None:
        """Selects remote addr from the given list of ips in
        X-Forwarded-For. Picks first non-trusted ip address.
        """
        trusted_proxies: list[str] = ["127.0.0.1", "::1"]
        remote_addr: str | None = self.remote_addr
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

    def get_str_input(self, varname: str, deflt: str | None = None) -> str | None:
        return self.var(varname, deflt)

    def get_str_input_mandatory(self, varname: str, deflt: str | None = None) -> str:
        return mandatory_parameter(varname, self.get_str_input(varname, deflt))

    def get_model_mandatory(
        self,
        model: type[Model_T],
        varname: str,
    ) -> Model_T:
        """Try to convert the value of an HTTP request variable to a given pydantic model"""
        try:
            return model.model_validate_json(mandatory_parameter(varname, self.var(varname)))
        except ValueError as exception:
            raise MKUserError(varname, _("The value is not valid: '%s'") % exception)

    @overload
    def get_validated_type_input(
        self,
        type_: type[Validation_T],
        varname: str,
        *,
        empty_is_none: bool = False,
    ) -> Validation_T | None: ...

    @overload
    def get_validated_type_input(
        self,
        type_: type[Validation_T],
        varname: str,
        deflt: None,
        *,
        empty_is_none: bool = False,
    ) -> Validation_T | None: ...

    @overload
    def get_validated_type_input(
        self,
        type_: type[Validation_T],
        varname: str,
        deflt: Validation_T,
        *,
        empty_is_none: bool = False,
    ) -> Validation_T: ...

    def get_validated_type_input(
        self,
        type_: type[Validation_T],
        varname: str,
        deflt: Validation_T | None = None,
        *,
        empty_is_none: bool = False,
    ) -> Validation_T | None:
        """Try to convert the value of an HTTP request variable to a given type

        If empty_is_none is set to True, treat variables that are present but empty as
        if they were missing (and return the default).

        The Checkmk UI excepts `MKUserError` *exceptions* to be raised by
        validation errors. In this case, the UI displays a textual error message to the
        user without triggering a crash report. The `ValueError` *exceptions* raised by
        the `__new__` method of `type_` are caught and re-raised as `MKUserError` to
        trigger the intended error handling.
        """
        raw_value = self.var(varname)
        if raw_value is None:
            return deflt
        if empty_is_none and not raw_value:
            return deflt
        try:
            return type_(raw_value)
        except ValueError as exception:
            raise MKUserError(varname, _("The value is not valid: '%s'") % exception)

    def get_validated_type_input_mandatory(
        self,
        type_: type[Validation_T],
        varname: str,
        deflt: Validation_T | None = None,
        *,
        empty_is_none: bool = False,
    ) -> Validation_T:
        """Like get_validated_type_input, but raise an error if the input is missing"""
        return mandatory_parameter(
            varname,
            self.get_validated_type_input(type_, varname, deflt, empty_is_none=empty_is_none),
        )

    def get_ascii_input(self, varname: str, deflt: str | None = None) -> str | None:
        """Helper to retrieve a byte string and ensure it only contains ASCII characters
        In case a non-ASCII character is found an MKUserError() is raised."""
        value = self.get_str_input(varname, deflt)
        if value is None:
            return value
        if not value.isascii():
            raise MKUserError(varname, _("The given text must only contain ASCII characters."))
        return value

    def get_ascii_input_mandatory(
        self, varname: str, deflt: str | None = None, allowed_values: set[str] | None = None
    ) -> str:
        value = mandatory_parameter(varname, self.get_ascii_input(varname, deflt))
        if allowed_values is not None and value not in allowed_values:
            raise MKUserError(varname, _("Value must be one of '%s'") % "', '".join(allowed_values))
        return value

    def get_binary_input(self, varname: str, deflt: bytes | None = None) -> bytes | None:
        val = self.var(varname, deflt.decode() if deflt is not None else None)
        if val is None:
            return None
        return val.encode()

    def get_binary_input_mandatory(self, varname: str, deflt: bytes | None = None) -> bytes:
        return mandatory_parameter(varname, self.get_binary_input(varname, deflt))

    def get_integer_input(self, varname: str, deflt: int | None = None) -> int | None:
        value = self.var(varname, "%d" % deflt if deflt is not None else None)
        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            raise MKUserError(varname, _('The parameter "%s" is not an integer.') % varname)

    def get_integer_input_mandatory(self, varname: str, deflt: int | None = None) -> int:
        return mandatory_parameter(varname, self.get_integer_input(varname, deflt))

    def get_float_input(self, varname: str, deflt: float | None = None) -> float | None:
        value = self.var(varname, "%s" % deflt if deflt is not None else None)
        if value is None:
            return None

        try:
            return float(value)
        except ValueError:
            raise MKUserError(varname, _('The parameter "%s" is not a float.') % varname)

    def get_float_input_mandatory(self, varname: str, deflt: float | None = None) -> float:
        return mandatory_parameter(varname, self.get_float_input(varname, deflt))

    def get_item_input(self, varname: str, collection: Mapping[str, Value]) -> tuple[Value, str]:
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
    def get_url_input(self, varname: str, deflt: str | None = None) -> str:
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

        if not is_allowed_url(url):
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
    def get_request(self, exclude_vars: list[str] | None = None) -> dict[str, Any]:
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


class Response(flask.Response):
    # NOTE: Currently we rely on a *relative* Location header in redirects!
    autocorrect_location_header = False

    default_mimetype = "text/html"

    def set_http_cookie(self, key: str, value: str, *, secure: bool) -> None:
        super().set_cookie(
            key, value, path=url_prefix(), secure=secure, httponly=True, samesite="Lax"
        )

    def unset_http_cookie(self, key: str) -> None:
        super().delete_cookie(key, path=url_prefix())

    def set_content_type(self, mime_type: str) -> None:
        self.headers["Content-type"] = get_content_type(mime_type, "utf-8")

    def set_csp_form_action(self, form_action: str) -> None:
        """If you have a form action that is not within the site, the
        Content-Security-Policy will block it. So you can add it here, Apache
        will then take this value and complete the CSP"""

        self.headers["Content-Security-Policy"] = (
            f"form-action 'self' javascript: 'unsafe-inline' {form_action};"
        )

    def set_content_disposition(self, header_type: ContentDispositionType, filename: str) -> None:
        """Define the Content-Disposition header here, this HTTP header controls how
        browsers present download data. If you are providing custom meta data for
        the filename and process (such as attachment, inline etc) by which a browser
        should make use when downloading.
        """

        if '"' in filename or "\\" in filename:
            raise ValueError("Invalid character in filename")
        for extensions in FILE_EXTENSIONS.get(str(self.mimetype), []):
            if filename.endswith(extensions):
                break
        else:
            raise ValueError("Invalid file extension: Have you set the Content-Type header?")
        self.headers["Content-Disposition"] = f'{header_type}; filename="{filename}"'

    def set_caching_headers(self) -> None:
        if "Cache-Control" in self.headers:
            # Do not override previous set settings
            return
        self.headers["Cache-Control"] = "no-store"


# From request context
request: Request = cast(Request, flask_request)
response = request_local_attr("response", Response)
