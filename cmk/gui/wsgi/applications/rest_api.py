#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import base64
import binascii
import contextlib
import functools
import http.client
import json
import logging
import mimetypes
import os
import re
import traceback
import urllib.parse
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any, Generator, TYPE_CHECKING

from apispec.yaml_utils import dict_to_yaml
from flask import g
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule, Submount

from cmk.utils import crash_reporting, paths
from cmk.utils.exceptions import MKException
from cmk.utils.type_defs import UserId

import cmk.gui.session
from cmk.gui import config, userdb
from cmk.gui.auth import (
    automation_auth,
    check_auth_by_cookie,
    gui_user_auth,
    rfc7662_subject,
    user_from_bearer_header,
)
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.http import Request, Response
from cmk.gui.logged_in import user
from cmk.gui.openapi import add_once, ENDPOINT_REGISTRY, generate_data
from cmk.gui.plugins.openapi.utils import problem, ProblemException
from cmk.gui.session import UserContext
from cmk.gui.wsgi.wrappers import ParameterDict

if TYPE_CHECKING:
    # TODO: Directly import from wsgiref.types in Python 3.11, without any import guard
    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment

    from cmk.gui.plugins.openapi.restful_objects import Endpoint
    from cmk.gui.plugins.openapi.restful_objects.type_defs import EndpointTarget
    from cmk.gui.wsgi.type_defs import RFC7662, WSGIResponse

ARGS_KEY = "CHECK_MK_REST_API_ARGS"

logger = logging.getLogger("cmk.gui.wsgi.rest_api")

EXCEPTION_STATUS: dict[type[Exception], int] = {
    MKUserError: 400,
    MKAuthException: 401,
}


def _verify_user(  # pylint: disable=too-many-branches
    environ: WSGIEnvironment,
    now: datetime,
) -> RFC7662:
    verified: list[RFC7662] = []

    auth_header = environ.get("HTTP_AUTHORIZATION", "")
    basic_user = None
    if auth_header:
        auth_type, _ = auth_header.split(None, 1)
        if auth_type == "Bearer":
            user_id, secret = user_from_bearer_header(auth_header)
            automation_user = automation_auth(user_id, secret)
            if automation_user:
                verified.append(automation_user)
            else:
                # GUI user and Automation users are mutually exclusive. Checking only once is less
                # work for the system.
                gui_user = gui_user_auth(user_id, secret, now)
                if gui_user:
                    verified.append(gui_user)
        elif auth_type == "Basic":
            # We store this for sanity checking below, once we get a REMOTE_USER key.
            # If we don't get a REMOTE_USER key, this value will be ignored.
            basic_user = user_from_basic_header(auth_header)
        else:
            raise MKAuthException(f"Unsupported Auth Type: {auth_type}")

    remote_user = environ.get("REMOTE_USER", "")
    if remote_user and userdb.user_exists(UserId(remote_user)):
        if basic_user and basic_user[0] != remote_user:
            raise MKAuthException("Mismatch in authentication headers.")
        verified.append(rfc7662_subject(UserId(remote_user), "web_server"))

    cookie_user = check_auth_by_cookie()
    if cookie_user is not None:
        verified.append(rfc7662_subject(cookie_user, "cookie"))

    if not verified:
        raise MKAuthException("You need to be authenticated to use the REST API.")

    # We pick the first successful authentication method, which means the precedence is the same
    # as the order in the code.
    final_candidate = verified[0]
    user_id = final_candidate["sub"]
    if not userdb.is_customer_user_allowed_to_login(user_id):
        raise MKAuthException(f"{user_id} may not log in here.")

    if userdb.user_locked(user_id):
        raise MKAuthException(f"{user_id} not authorized.")

    if change_reason := userdb.need_to_change_pw(user_id, now):
        raise MKAuthException(f"{user_id} needs to change the password ({change_reason}).")

    if userdb.is_two_factor_login_enabled(user_id):
        if final_candidate["scope"] != "cookie":
            raise MKAuthException(
                f"{user_id} has two-factor authentication enabled, which can only be used in "
                "interactive GUI sessions."
            )
        if not cmk.gui.session.is_two_factor_completed():
            raise MKAuthException("The two-factor authentication needs to be passed first.")

    return final_candidate


def user_from_basic_header(auth_header: str) -> tuple[UserId, str]:
    """Decode a Basic Authorization header

    Examples:

        >>> user_from_basic_header("Basic Zm9vYmF6YmFyOmZvb2JhemJhcg==")
        ('foobazbar', 'foobazbar')

        >>> import pytest

        >>> with pytest.raises(MKAuthException):
        ...     user_from_basic_header("Basic SGFsbG8gV2VsdCE=")  # 'Hallo Welt!'

        >>> with pytest.raises(MKAuthException):
        ...     user_from_basic_header("Basic foobazbar")

        >>> with pytest.raises(MKAuthException):
        ...      user_from_basic_header("Basic     ")

    Args:
        auth_header:

    Returns:

    """
    try:
        _, token = auth_header.split("Basic ", 1)
    except ValueError as exc:
        raise MKAuthException("Not a valid Basic token.") from exc

    if not token.strip():
        raise MKAuthException("Not a valid Basic token.")

    try:
        user_entry = base64.b64decode(token.strip()).decode("latin1")
    except binascii.Error as exc:
        raise MKAuthException("Not a valid Basic token.") from exc

    try:
        user_id, secret = user_entry.split(":")
    except ValueError as exc:
        raise MKAuthException("Not a valid Basic token.") from exc

    return UserId(user_id), secret


class Authenticate:
    """Authenticate all URLs going into the wrapped WSGI application"""

    def __init__(self, app: WSGIApplication) -> None:
        self.app = app

    def __repr__(self) -> str:
        return f"<Authenticate {self.app!r}>"

    def __get__(self, instance, owner=None):
        return functools.partial(self.wsgi_app, instance)

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        try:
            rfc7662 = _verify_user(environ, datetime.now())
        except MKException as exc:
            return problem(status=401, title=str(exc))(environ, start_response)
        with set_user_context(rfc7662["sub"], rfc7662):
            return self.app(environ, start_response)


class EndpointAdapter:
    """Wrap an Endpoint

    Makes a "real" WSGI application out of an endpoint. Should be refactored away.
    """

    def __init__(self, endpoint: Endpoint) -> None:
        self.endpoint = endpoint

    def __repr__(self) -> str:
        return f"<EndpointAdapter {self.endpoint!r}>"

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        path_args = environ[ARGS_KEY]

        # Create the response
        with self.endpoint.register_permission_tracking():
            wsgi_app = self.endpoint.wrapped(ParameterDict(path_args))

        # Serve the response
        return wsgi_app(environ, start_response)


@functools.lru_cache
def serve_file(  # type:ignore[no-untyped-def]
    file_name: str,
    content: bytes,
    default_content_type="text/plain; charset=utf-8",
) -> Response:
    """Construct and cache a Response from a static file."""
    content_type, _ = mimetypes.guess_type(file_name)

    resp = Response()
    resp.direct_passthrough = True
    resp.data = content
    if content_type is not None:
        resp.headers["Content-Type"] = content_type
    else:
        resp.headers["Content-Type"] = default_content_type
    resp.freeze()
    return resp


def get_url(environ: WSGIEnvironment) -> str:
    """Reconstruct a URL from a WSGI environment

    >>> get_url({
    ...     'HTTP_HOST': 'localhorst',
    ...     'SERVER_PORT': '81',
    ...     'SERVER_NAME': 'localhost',
    ...     'wsgi.url_scheme': 'http',
    ... })
    '//localhorst'

    >>> get_url({
    ...     'SERVER_PORT': '443',
    ...     'SERVER_NAME': 'localhost',
    ...     'wsgi.url_scheme': 'https',
    ...     'PATH_INFO': '/NO_SITE/check_mk/view.py'
    ... })
    '//localhost/NO_SITE/check_mk/view.py'

    Args:
        environ:
            A WSGI environment

    Returns:
        A HTTP URL.

    """
    # We construct a protocol relative URL so we don't need to know if we are on HTTP or HTTPs.
    # This is important if we are behind a SSL terminating HTTP application proxy, which doesn't
    # forward the protocol used. This solution is more robust in those circumstances.
    if environ.get("HTTP_HOST"):
        host_name = environ["HTTP_HOST"]
    else:
        host_name = environ["SERVER_NAME"]

    return f"//{host_name}{urllib.parse.quote(environ.get('PATH_INFO', ''))}"


@functools.lru_cache(maxsize=512)
def serve_spec(
    site: str,
    target: EndpointTarget,
    url: str,
    content_type: str,
    serializer: Callable[[dict[str, Any]], str],
) -> Response:
    data = generate_data(target=target)
    data.setdefault("servers", [])
    add_once(
        data["servers"],
        {
            "url": url,
            "description": f"Site: {site}",
        },
    )
    response = Response(status=200)
    response.data = serializer(data)
    response.content_type = content_type
    response.freeze()
    return response


class ServeSpec:
    def __init__(self, target: EndpointTarget, extension: str) -> None:
        self.target = target
        self.extension = extension

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        serializers = {"yaml": dict_to_yaml, "json": json.dumps}
        content_types = {
            "json": "application/json",
            "yaml": "application/x-yaml; charset=utf-8",
        }
        return serve_spec(
            site=_site(environ),
            target=self.target,
            url=_url(environ),
            content_type=content_types[self.extension],
            serializer=serializers[self.extension],
        )(environ, start_response)


def _site(environ: WSGIEnvironment) -> str:
    path_info = environ["PATH_INFO"].split("/")
    return path_info[1]


def _url(environ: WSGIEnvironment) -> str:
    return "/".join(get_url(environ).split("/")[:-1])


class ServeSwaggerUI:
    def __init__(self, prefix="") -> None:  # type:ignore[no-untyped-def]
        self.prefix = prefix
        self.data: dict[str, Any] | None = None

    def _relative_path(self, environ: WSGIEnvironment) -> str:
        path_info = environ["PATH_INFO"]
        relative_path = re.sub(self.prefix, "", path_info)
        if relative_path == "/":
            relative_path = "/index.html"
        return relative_path

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self._serve_file(environ, start_response)

    def _serve_file(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        current_url = get_url(environ)
        yaml_filename = "openapi-swagger-ui.yaml"
        if current_url.endswith("/ui/"):
            current_url = current_url[:-4]

        yaml_file = f"{current_url}/{yaml_filename}"
        file_path = f"{paths.web_dir}/htdocs/openapi/swagger-ui-3/{self._relative_path(environ)}"

        if not os.path.exists(file_path):
            return NotFound()(environ, start_response)

        with open(file_path, "rb") as fh:
            content: bytes = fh.read()

        if file_path.endswith("/index.html"):
            page = []
            for line in content.splitlines():
                if b"<title>" in line:
                    page.append(b"<title>REST-API Interactive GUI - Checkmk</title>")
                elif b"favicon" in line:
                    continue
                elif b"petstore.swagger.io" in line:
                    page.append(f'        url: "{yaml_file}",'.encode())
                    page.append(b"        validatorUrl: null,")
                    page.append(b"        displayOperationId: false,")
                else:
                    page.append(line)

            content = b"\n".join(page)

        return serve_file(file_path, content)(environ, start_response)


class CheckmkRESTAPI:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        # This intermediate data structure is necessary because `Rule`s can't contain anything
        # other than str anymore. Technically they could, but the typing is now fixed to str.
        self.endpoints: dict[str, WSGIApplication] = {
            "swagger-ui": ServeSwaggerUI(prefix="/[^/]+/check_mk/api/[^/]+/ui"),
            "swagger-ui-yaml": ServeSpec("swagger-ui", "yaml"),
            "swagger-ui-json": ServeSpec("swagger-ui", "json"),
            "doc-yaml": ServeSpec("doc", "yaml"),
            "doc-json": ServeSpec("doc", "json"),
        }
        self._url_map: Map | None = None

    def _build_url_map(self) -> Map:
        rules: list[Rule] = []
        endpoint: Endpoint
        for endpoint in ENDPOINT_REGISTRY:
            if self.debug:
                # This helps us to make sure we can always generate a valid OpenAPI yaml file.
                _ = endpoint.to_operation_dict()

            rules.append(
                Rule(
                    endpoint.default_path,
                    methods=[endpoint.method],
                    endpoint=endpoint.ident,
                )
            )
            self.endpoints[endpoint.ident] = EndpointAdapter(endpoint)

        return Map(
            [
                Submount(
                    "/<path:_path>",
                    [
                        Rule("/ui/", endpoint="swagger-ui"),
                        Rule("/ui/<path:path>", endpoint="swagger-ui"),
                        Rule("/openapi-swagger-ui.yaml", endpoint="swagger-ui-yaml"),
                        Rule("/openapi-swagger-ui.json", endpoint="swagger-ui-json"),
                        Rule("/openapi-doc.yaml", endpoint="doc-yaml"),
                        Rule("/openapi-doc.json", endpoint="doc-json"),
                        *rules,
                    ],
                )
            ]
        )

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        try:
            if self._url_map is None:
                # NOTE: This needs to be executed in a Request context because it depends on
                # the configuration
                self._url_map = self._build_url_map()

            urls = self._url_map.bind_to_environ(environ)
            result: tuple[str, Mapping[str, Any]] = urls.match(return_rule=False)
            endpoint_ident, matched_path_args = result  # pylint: disable=unpacking-non-sequence
            wsgi_app = self.endpoints[endpoint_ident]
            if isinstance(wsgi_app, EndpointAdapter):
                g.endpoint = wsgi_app.endpoint

            # Remove _path again (see Submount above), so the validators don't go crazy.
            path_args = {key: value for key, value in matched_path_args.items() if key != "_path"}

            # This is an implicit dependency, as we only know the args at runtime, but the
            # function at setup-time.
            environ[ARGS_KEY] = path_args

            return wsgi_app(environ, start_response)
        except ProblemException as exc:
            return exc(environ, start_response)
        except HTTPException as exc:
            # We don't want to log explicit HTTPExceptions as these are intentional.
            assert isinstance(exc.code, int)
            return problem(
                status=exc.code,
                title=http.client.responses[exc.code],
                detail=str(exc),
            )(environ, start_response)
        except MKException as exc:
            if self.debug:
                raise

            return problem(
                status=EXCEPTION_STATUS.get(type(exc), 500),
                title="An exception occurred.",
                detail=str(exc),
            )(environ, start_response)
        except Exception as exc:
            crash = APICrashReport.from_exception()
            crash_reporting.CrashReportStore().save(crash)
            logger.exception("Unhandled exception (Crash-ID: %s)", crash.ident_to_text())
            if self.debug:
                raise

            request = Request(environ)
            site = config.omd_site()
            query_string = urllib.parse.urlencode(
                [
                    ("crash_id", (crash.ident_to_text())),
                    ("site", site),
                ]
            )
            crash_url = f"{request.host_url}{site}/check_mk/crash.py?{query_string}"
            crash_details = {
                "crash_id": (crash.ident_to_text()),
                "crash_report": {
                    "href": crash_url,
                    "method": "get",
                    "rel": "cmk/crash-report",
                    "type": "text/html",
                },
            }
            if user.may("general.see_crash_reports"):
                crash_details["stack_trace"] = traceback.format_exc().split("\n")

            return problem(
                status=500,
                title=http.client.responses[500],
                detail=str(exc),
                ext=crash_details,
            )(environ, start_response)


class APICrashReport(crash_reporting.ABCCrashReport):
    """API specific crash reporting class."""

    @classmethod
    def type(cls):
        return "rest_api"


@contextlib.contextmanager
def set_user_context(user_id: UserId, token_info: RFC7662) -> Generator[None, None, None]:
    if user_id and token_info and user_id == token_info.get("sub"):
        with UserContext(user_id):
            yield
    else:
        raise MKAuthException("Unauthorized by verify_user")
