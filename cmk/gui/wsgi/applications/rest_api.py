#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import functools
import json
import logging
import mimetypes
import re
import urllib.parse
from typing import Dict, Type, Any, Optional, Callable

from apispec.yaml_utils import dict_to_yaml  # type: ignore[import]
from swagger_ui_bundle import swagger_ui_3_path  # type: ignore[import]
from werkzeug import Response, Request
from werkzeug.exceptions import HTTPException

from werkzeug.routing import Map, Submount, Rule

from cmk.gui import config
from cmk.gui.config import omd_site
from cmk.gui.exceptions import MKUserError, MKAuthException
from cmk.gui.login import check_parsed_auth_cookie
from cmk.gui.openapi import ENDPOINT_REGISTRY, generate_data
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.wsgi.auth import verify_user, bearer_auth, rfc7662_subject
from cmk.gui.wsgi.middleware import with_context_middleware, OverrideRequestMethod
from cmk.gui.wsgi.type_defs import RFC7662
from cmk.gui.wsgi.wrappers import ParameterDict
from cmk.utils import crash_reporting
from cmk.utils.exceptions import MKException
from cmk.utils.type_defs import UserId

ARGS_KEY = 'CHECK_MK_REST_API_ARGS'

logger = logging.getLogger('cmk.gui.wsgi.rest_api')

EXCEPTION_STATUS: Dict[Type[Exception], int] = {
    MKUserError: 400,
    MKAuthException: 401,
}

WSGIEnvironment = Dict[str, Any]


def _verify_request(environ) -> RFC7662:
    auth_header = environ.get('HTTP_AUTHORIZATION', '')
    if auth_header:
        return bearer_auth(auth_header)

    cookie = Request(environ).cookies.get(f"auth_{omd_site()}")
    if cookie:
        try:
            username, session_id, cookie_hash = cookie.split(':', 2)
        except ValueError:
            raise MKAuthException("Invalid auth cookie.")
        check_parsed_auth_cookie(UserId(username), session_id, cookie_hash)
        return rfc7662_subject(username, 'cookie')

    raise MKAuthException("You need to be authenticated to use the REST API.")


class Authenticate:
    """Wrap an Endpoint so it will be authenticated

    This is not very memory efficient as it wraps every individual endpoint in its own
    authenticator, even though this does not need to be. This has to be done this way right now,
    because we have multiple endpoints without authentication in this app. A refactoring to lower
    the memory foot-print of this is feasible and should be done if a good way has been found.
    """
    def __init__(self, func):
        self.func = func

    def __call__(self, environ, start_response):
        path_args = environ[ARGS_KEY]

        try:
            rfc7662 = _verify_request(environ)
        except MKException as exc:
            return problem(
                status=401,
                title=str(exc),
            )(environ, start_response)

        with verify_user(rfc7662['sub'], rfc7662):
            wsgi_app = self.func(ParameterDict(path_args))
            return wsgi_app(environ, start_response)


@functools.lru_cache
def serve_file(file_name: str, content: str) -> Response:
    content_type, _ = mimetypes.guess_type(file_name)

    resp = Response()
    resp.direct_passthrough = True
    resp.data = content
    if content_type is not None:
        resp.headers['Content-Type'] = content_type
    resp.freeze()
    return resp


def get_url(environ: WSGIEnvironment) -> str:
    url = environ['wsgi.url_scheme'] + '://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']

    url += urllib.parse.quote(environ.get('PATH_INFO', ''))

    return url


@functools.lru_cache(maxsize=512)
def serve_spec(
    site: str,
    url: str,
    content_type: str,
    serializer: Callable[[Dict[str, Any]], str],
) -> Response:
    data = generate_data()
    data.setdefault('servers', [])
    data['servers'].append({
        'url': url,
        'description': f"Site: {site}",
    })
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

    def serve_json(self, environ: WSGIEnvironment, start_response):
        return serve_spec(
            site=self._site(environ),
            url=self._url(environ),
            content_type='application/json',
            serializer=json.dumps,
        )(environ, start_response)

    def serve_yaml(self, environ: WSGIEnvironment, start_response):
        return serve_spec(
            site=self._site(environ),
            url=self._url(environ),
            content_type='application/x-yaml; charset=utf-8',
            serializer=dict_to_yaml,
        )(environ, start_response)

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
        if current_url.endswith("/ui/"):
            yaml_file = current_url[:-4] + "/openapi.yaml"
        else:
            yaml_file = current_url + "/openapi.yaml"

        file_path = swagger_ui_3_path + self._relative_path(environ)

        with open(file_path) as fh:
            content = fh.read()

        if file_path.endswith("/index.html"):
            content = content.replace("<title>Swagger UI</title>",
                                      "<title>REST-API Interactive GUI - Checkmk</title>")
            content = content.replace("https://petstore.swagger.io/v2/swagger.json", yaml_file)
            content = content.replace(
                "        dom_id",
                '        validatorUrl: null,\n        dom_id',
            )
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
                Rule(endpoint.default_path,
                     methods=[endpoint.method],
                     endpoint=Authenticate(endpoint.wrapped)))

        swagger_ui = ServeSwaggerUI(prefix="/[^/]+/check_mk/api/[^/]+/ui")

        self.url_map = Map([
            Submount(
                "/<path:_path>",
                [
                    Rule("/ui/", endpoint=swagger_ui),
                    Rule("/ui/<path:path>", endpoint=swagger_ui),
                    Rule("/openapi.yaml", endpoint=swagger_ui.serve_yaml),
                    Rule("/openapi.json", endpoint=swagger_ui.serve_json),
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
            return wsgi_app(environ, start_response)
        except HTTPException as exc:
            # We don't want to log explicit HTTPExceptions as these are intentional.
            # HTTPExceptions are WSGI apps
            return exc(environ, start_response)
        except MKException as exc:
            if self.debug:
                raise

            return problem(
                status=EXCEPTION_STATUS.get(type(exc), 500),
                title=str(exc),
                detail="An exception occurred.",
            )(environ, start_response)
        except Exception as exc:
            crash = APICrashReport.from_exception()
            crash_reporting.CrashReportStore().save(crash)
            logger.exception("Unhandled exception (Crash-ID: %s)", crash.ident_to_text())
            if self.debug:
                raise

            crash_url = f"/{config.omd_site()}/check_mk/crash.py?" + urllib.parse.urlencode([
                ("crash_id", crash.ident_to_text()),
                ("site", config.omd_site()),
            ],)

            return problem(status=EXCEPTION_STATUS.get(type(exc), 500),
                           title=str(exc),
                           detail="An internal error occured while processing your request.",
                           ext={
                               'crash_report': {
                                   'href': crash_url,
                                   'method': 'get',
                                   'rel': 'cmk/crash-report',
                                   'type': 'text/html',
                               },
                               'crash_id': crash.ident_to_text(),
                           })(environ, start_response)


class APICrashReport(crash_reporting.ABCCrashReport):
    """API specific crash reporting class.
    """
    @classmethod
    def type(cls):
        return "rest_api"
