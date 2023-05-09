#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import traceback

import binascii
import functools
import http.client
import json
import logging
import mimetypes
import os
import re
import urllib.parse
from typing import Any, Callable, Dict, Optional, Tuple, Type, List, Literal

from apispec.yaml_utils import dict_to_yaml  # type: ignore[import]
from werkzeug import Request, Response
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule, Submount

from cmk.utils import crash_reporting, paths
from cmk.utils.exceptions import MKException
from cmk.utils.type_defs import UserId

from cmk.gui import config, userdb
from cmk.gui.exceptions import MKUserError, MKAuthException
from cmk.gui.login import check_cookie_restapi
from cmk.gui.openapi import ENDPOINT_REGISTRY, generate_data, add_once
from cmk.gui.plugins.openapi.restful_objects.type_defs import EndpointTarget
from cmk.gui.plugins.openapi.utils import problem, ProblemException
from cmk.gui.wsgi.auth import automation_auth, gui_user_auth, rfc7662_subject, set_user_context
from cmk.gui.wsgi.middleware import with_context_middleware, OverrideRequestMethod
from cmk.gui.wsgi.type_defs import RFC7662
from cmk.gui.wsgi.wrappers import ParameterDict

ARGS_KEY = 'CHECK_MK_REST_API_ARGS'

logger = logging.getLogger('cmk.gui.wsgi.rest_api')

EXCEPTION_STATUS: Dict[Type[Exception], int] = {
    MKUserError: 400,
    MKAuthException: 401,
}

SpecExtension = Literal['json', 'yaml']
WSGIEnvironment = Dict[str, Any]


def _verify_user(environ) -> RFC7662:
    verified: List[RFC7662] = []

    auth_header = environ.get('HTTP_AUTHORIZATION', '')
    basic_user = None
    if auth_header:
        auth_type, _ = auth_header.split(None, 1)
        if auth_type == 'Bearer':
            user_id, secret = user_from_bearer_header(auth_header)
            automation_user = automation_auth(user_id, secret)
            if automation_user:
                verified.append(automation_user)
            else:
                # GUI user and Automation users are mutually exclusive. Checking only once is less
                # work for the system.
                gui_user = gui_user_auth(user_id, secret)
                if gui_user:
                    verified.append(gui_user)
        elif auth_type == 'Basic':
            # We store this for sanity checking below, once we get a REMOTE_USER key.
            # If we don't get a REMOTE_USER key, this value will be ignored.
            basic_user = user_from_basic_header(auth_header)
        else:
            raise MKAuthException(f"Unsupported Auth Type: {auth_type}")

    remote_user = environ.get('REMOTE_USER', '')
    if remote_user and userdb.user_exists(UserId(remote_user)):
        if basic_user and basic_user[0] != remote_user:
            raise MKAuthException("Mismatch in authentication headers.")
        verified.append(rfc7662_subject(UserId(remote_user), 'webserver'))

    cookie_user = check_cookie_restapi()
    if cookie_user is not None:
        verified.append(rfc7662_subject(cookie_user, "cookie"))

    if not verified:
        raise MKAuthException("You need to be authenticated to use the REST API.")

    # We pick the first successful authentication method, which means the precedence is the same
    # as the oder in the code.
    final_candidate = verified[0]
    if not userdb.is_customer_user_allowed_to_login(final_candidate['sub']):
        raise MKAuthException(f"{final_candidate['sub']} may not log in here.")

    if userdb.user_locked(final_candidate['sub']):
        raise MKAuthException(f"{final_candidate['sub']} not authorized.")

    return final_candidate


def user_from_basic_header(auth_header: str) -> Tuple[UserId, str]:
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
        user_entry = base64.b64decode(token.strip()).decode('latin1')
    except binascii.Error as exc:
        raise MKAuthException("Not a valid Basic token.") from exc

    try:
        user_id, secret = user_entry.split(":")
    except ValueError as exc:
        raise MKAuthException("Not a valid Basic token.") from exc

    return UserId(user_id), secret


def user_from_bearer_header(auth_header: str) -> Tuple[UserId, str]:
    """

    Examples:

        >>> user_from_bearer_header("Bearer username password")
        ('username', 'password')

    Args:
        auth_header:

    Returns:

    """
    try:
        _, token = auth_header.split("Bearer ", 1)
    except ValueError:
        raise MKAuthException(f"Not a valid Bearer token: {auth_header}")
    try:
        user_id, secret = token.strip().split(' ', 1)
    except ValueError:
        raise MKAuthException("No user/password combination in Bearer token.")
    if not secret:
        raise MKAuthException("Empty password not allowed.")
    if not user_id:
        raise MKAuthException("Empty user not allowed.")
    if "/" in user_id:
        raise MKAuthException("No slashes / allowed in username.")

    return UserId(user_id), secret


class EndpointAdapter:
    """Wrap an Endpoint

    Makes a "real" WSGI application out of an endpoint. Should be refactored away.
    """
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def __call__(self, environ, start_response):
        path_args = environ[ARGS_KEY]
        wsgi_app = self.endpoint.wrapped(ParameterDict(path_args))
        return wsgi_app(environ, start_response)


@functools.lru_cache
def serve_file(file_name: str, content: bytes) -> Response:
    """Construct and cache a Response from a static file."""
    content_type, _ = mimetypes.guess_type(file_name)

    resp = Response()
    resp.direct_passthrough = True
    resp.data = content
    if content_type is not None:
        resp.headers['Content-Type'] = content_type
    resp.freeze()
    return resp


def get_url(environ: WSGIEnvironment) -> str:
    """Reconstruct an URL from a WSGI environment

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
    if environ.get('HTTP_HOST'):
        host_name = environ['HTTP_HOST']
    else:
        host_name = environ['SERVER_NAME']

    return f"//{host_name}{urllib.parse.quote(environ.get('PATH_INFO', ''))}"


@functools.lru_cache(maxsize=512)
def serve_spec(
    site: str,
    target: EndpointTarget,
    url: str,
    content_type: str,
    serializer: Callable[[Dict[str, Any]], str],
) -> Response:
    data = generate_data(target=target)
    data.setdefault('servers', [])
    add_once(data['servers'], {'url': url, 'description': f"Site: {site}"})
    response = Response(status=200)
    response.data = serializer(data)
    response.content_type = content_type
    response.freeze()
    return response


class ServeSwaggerUI:
    def __init__(self, prefix=''):
        self.prefix = prefix
        self.data: Optional[Dict[str, Any]] = None

    def _site(self, environ: WSGIEnvironment):
        path_info = environ['PATH_INFO'].split("/")
        return path_info[1]

    def _url(self, environ: WSGIEnvironment):
        return '/'.join(get_url(environ).split("/")[:-1])

    def serve_spec(self, target: EndpointTarget, extension: SpecExtension):
        def _serve(environ: WSGIEnvironment, start_response):
            serializers = {
                'yaml': dict_to_yaml,
                'json': json.dumps,
            }
            content_types = {
                'json': 'application/json',
                'yaml': 'application/x-yaml; charset=utf-8'
            }
            return serve_spec(
                site=self._site(environ),
                target=target,
                url=self._url(environ),
                content_type=content_types[extension],
                serializer=serializers[extension],
            )(environ, start_response)

        return _serve

    def _relative_path(self, environ: WSGIEnvironment):
        path_info = environ['PATH_INFO']
        relative_path = re.sub(self.prefix, '', path_info)
        if relative_path == "/":
            relative_path = "/index.html"
        return relative_path

    def __call__(self, environ: WSGIEnvironment, start_response):
        return self._serve_file(environ, start_response)

    def _serve_file(self, environ, start_response):
        current_url = get_url(environ)
        yaml_filename = "openapi-swagger-ui.yaml"
        if current_url.endswith("/ui/"):
            current_url = current_url[:-4]

        yaml_file = f"{current_url}/{yaml_filename}"
        file_path = f"{paths.web_dir}/htdocs/openapi/swagger-ui-3/{self._relative_path(environ)}"

        if not os.path.exists(file_path):
            return NotFound()(environ, start_response)

        with open(file_path, 'rb') as fh:
            content: bytes = fh.read()

        if file_path.endswith("/index.html"):
            page = []
            for line in content.splitlines():
                if b"<title>" in line:
                    page.append(b"<title>REST-API Interactive GUI - Checkmk</title>")
                elif b"petstore.swagger.io" in line:
                    page.append(f'        url: "{yaml_file}",'.encode('utf-8'))
                    page.append(b'        validatorUrl: null,')
                    page.append(b'        displayOperationId: false,')
                else:
                    page.append(line)

            content = b'\n'.join(page)

        return serve_file(file_path, content)(environ, start_response)


class CheckmkRESTAPI:
    def __init__(self, debug: bool = False):
        self.debug = debug
        rules = []
        for endpoint in ENDPOINT_REGISTRY:
            if self.debug:
                # This helps us to make sure we can always generate a valid OpenAPI yaml file.
                _ = endpoint.to_operation_dict()

            rules.append(
                Rule(
                    endpoint.default_path,
                    methods=[endpoint.method],
                    endpoint=EndpointAdapter(endpoint),
                ))

        swagger_ui = ServeSwaggerUI(prefix="/[^/]+/check_mk/api/[^/]+/ui")

        self.url_map = Map([
            Submount(
                "/<path:_path>",
                [
                    Rule("/ui/", endpoint=swagger_ui),
                    Rule("/ui/<path:path>", endpoint=swagger_ui),
                    Rule("/openapi-swagger-ui.yaml",
                         endpoint=swagger_ui.serve_spec('swagger-ui', 'yaml')),
                    Rule("/openapi-swagger-ui.json",
                         endpoint=swagger_ui.serve_spec('swagger-ui', 'json')),
                    Rule("/openapi-doc.yaml", endpoint=swagger_ui.serve_spec('doc', 'yaml')),
                    Rule("/openapi-doc.json", endpoint=swagger_ui.serve_spec('doc', 'json')),
                    *rules,
                ],
            ),
        ])
        self.wsgi_app = with_context_middleware(OverrideRequestMethod(self._wsgi_app))

    def __call__(self, environ: WSGIEnvironment, start_response):
        return self.wsgi_app(environ, start_response)

    def _wsgi_app(self, environ: WSGIEnvironment, start_response):
        urls = self.url_map.bind_to_environ(environ)
        try:
            wsgi_app, path_args = urls.match()

            # Remove this again (see Submount above), so the validators don't go crazy.
            del path_args['_path']

            # This is an implicit dependency, as we only know the args at runtime, but the
            # function at setup-time.
            environ[ARGS_KEY] = path_args

            # Authenticate the user for all endpoints and sub-applications.
            try:
                rfc7662 = _verify_user(environ)
            except MKException as exc:
                return problem(
                    status=401,
                    title=str(exc),
                )(environ, start_response)

            with set_user_context(rfc7662["sub"], rfc7662):
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
            crash_id = crash.ident_to_text()
            logger.exception("Unhandled exception (Crash-ID: %s)", crash_id)
            if self.debug:
                raise

            request = Request(environ)
            site = config.omd_site()
            query_string = urllib.parse.urlencode([
                ("crash_id", crash_id),
                ("site", site),
            ])
            crash_url = f"{request.host_url}{site}/check_mk/crash.py?{query_string}"
            crash_details = {
                'crash_id': crash_id,
                'crash_report': {
                    'href': crash_url,
                    'method': 'get',
                    'rel': 'cmk/crash-report',
                    'type': 'text/html',
                },
            }
            if config.user.may("general.see_crash_reports"):
                crash_details['stack_trace'] = traceback.format_exc().split("\n")

            return problem(
                status=500,
                title=http.client.responses[500],
                detail=str(exc),
                ext=crash_details,
            )(environ, start_response)


class APICrashReport(crash_reporting.ABCCrashReport):
    """API specific crash reporting class.
    """
    @classmethod
    def type(cls):
        return "rest_api"
