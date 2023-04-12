#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import contextlib
import functools
import http.client
import json
import logging
import mimetypes
import traceback
import typing
import urllib.parse
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

from apispec.yaml_utils import dict_to_yaml
from flask import g, send_from_directory
from marshmallow import fields as ma_fields
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule, Submount

import cmk.utils.version as cmk_version
from cmk.utils import crash_reporting, paths
from cmk.utils.exceptions import MKException
from cmk.utils.type_defs import HTTPMethod

from cmk.gui import config, session
from cmk.gui.exceptions import MKAuthException, MKHTTPException, MKUserError
from cmk.gui.http import request, Response
from cmk.gui.logged_in import LoggedInNobody, user
from cmk.gui.openapi import add_once, ENDPOINT_REGISTRY, generate_data
from cmk.gui.plugins.openapi.restful_objects import Endpoint
from cmk.gui.plugins.openapi.restful_objects.parameters import (
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.plugins.openapi.utils import (
    EXT,
    GeneralRestAPIException,
    problem,
    ProblemException,
    RestAPIPermissionException,
    RestAPIRequestGeneralException,
    RestAPIResponseGeneralException,
)
from cmk.gui.wsgi.applications.utils import AbstractWSGIApp
from cmk.gui.wsgi.wrappers import ParameterDict

if TYPE_CHECKING:
    # TODO: Directly import from wsgiref.types in Python 3.11, without any import guard
    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment

    from cmk.gui.plugins.openapi.restful_objects.type_defs import EndpointTarget
    from cmk.gui.wsgi.type_defs import WSGIResponse

ARGS_KEY = "CHECK_MK_REST_API_ARGS"

logger = logging.getLogger("cmk.gui.wsgi.rest_api")

EXCEPTION_STATUS: dict[type[Exception], int] = {
    MKUserError: 400,
}

PathArgs = Mapping[str, Any]


def _get_header_name(header: Mapping[str, ma_fields.String]) -> str:
    assert len(header) == 1
    return next(iter(header))


def crash_report_response(exc: Exception) -> WSGIApplication:
    site = config.omd_site()
    details: dict[str, Any] = {}

    if isinstance(exc, GeneralRestAPIException):
        details["rest_api_exception"] = {
            "description": exc.description,
            "detail": exc.detail,
            "ext": exc.ext,
            "fields": exc.fields,
        }

    details["request_info"] = {
        "method": request.environ["REQUEST_METHOD"],
        "data_received": request.json if request.data else "",
        "endpoint_url": request.path,
        "headers": {
            "accept": request.environ.get("HTTP_ACCEPT", "missing"),
            "content_type": request.environ.get("CONTENT_TYPE", "missing"),
        },
    }

    details["check_mk_info"] = {
        "site": site,
        "check_mk_user": {
            "user_id": user.id,
            "user_roles": user.role_ids,
            "authorized_sites": list(user.authorized_sites()),
        },
    }

    crash = APICrashReport.from_exception(details=details)
    crash_reporting.CrashReportStore().save(crash)
    logger.exception("Unhandled exception (Crash-ID: %s)", crash.ident_to_text())

    query_string = urllib.parse.urlencode(
        [
            ("crash_id", (crash.ident_to_text())),
            ("site", site),
        ]
    )
    crash.crash_info["details"]["crash_report_url"] = {
        "href": f"{request.host_url}{site}/check_mk/crash.py?{query_string}",
        "method": "get",
        "rel": "cmk/crash-report",
        "type": "text/html",
    }

    del crash.crash_info["exc_traceback"]
    if user.may("general.see_crash_reports"):
        crash.crash_info["exc_traceback"] = traceback.format_exc().split("\n")

    crash.crash_info["time"] = datetime.fromtimestamp(crash.crash_info["time"]).isoformat()
    crash_msg = (
        exc.description
        if isinstance(exc, GeneralRestAPIException)
        else crash.crash_info["exc_value"]
    )

    return problem(
        status=500,
        title="Internal Server Error",
        detail=f"{crash.crash_info['exc_type']}: {crash_msg}. Crash report generated. Please submit.",
        ext=EXT(crash.crash_info),
    )


class EndpointAdapter(AbstractWSGIApp):
    """Wrap an Endpoint

    Makes a "real" WSGI application out of an endpoint. Should be refactored away.
    """

    def __init__(self, endpoint: Endpoint, debug: bool = False) -> None:
        super().__init__(debug)
        self.endpoint = endpoint

    def __repr__(self) -> str:
        return f"<EndpointAdapter {self.endpoint!r}>"

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        path_args = environ[ARGS_KEY]

        # Create the response
        with self.endpoint.register_permission_tracking():
            wsgi_app = self.endpoint.wrapped(ParameterDict(path_args))

        wsgi_app.headers[_get_header_name(HEADER_CHECKMK_VERSION)] = cmk_version.__version__
        wsgi_app.headers[_get_header_name(HEADER_CHECKMK_EDITION)] = cmk_version.edition().short

        # Serve the response
        return wsgi_app(environ, start_response)


@functools.lru_cache
def serve_file(  # type: ignore[no-untyped-def]
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


def get_filename_from_url(url: str) -> str:
    """return the filename of a url

    >>> get_filename_from_url("//foo/")
    ''
    >>> get_filename_from_url("//foo/bar/")
    ''
    >>> get_filename_from_url("//foo/bar?foo=bar")
    'bar'
    >>> get_filename_from_url("//foo/../foo/bar?foo=bar")
    'bar'
    """
    if url.endswith("/"):
        return ""
    return Path(urllib.parse.urlparse(url).path).name


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


class ServeSpec(AbstractWSGIApp):
    def __init__(self, target: EndpointTarget, extension: str, debug: bool = False) -> None:
        super().__init__(debug)
        self.target = target
        self.extension = extension

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        serializers = {"yaml": dict_to_yaml, "json": json.dumps}
        content_types = {
            "json": "application/json",
            "yaml": "application/x-yaml; charset=utf-8",
        }

        def _site(_environ: WSGIEnvironment) -> str:
            path_info = _environ["PATH_INFO"].split("/")
            return path_info[1]

        def _url(_environ: WSGIEnvironment) -> str:
            return "/".join(get_url(_environ).split("/")[:-1])

        return serve_spec(
            site=_site(environ),
            target=self.target,
            url=_url(environ),
            content_type=content_types[self.extension],
            serializer=serializers[self.extension],
        )(environ, start_response)


class ServeSwaggerUI(AbstractWSGIApp):
    def __init__(self, prefix: str = "", debug: bool = False) -> None:
        super().__init__(debug)
        self.prefix = prefix
        self.data: dict[str, Any] | None = None

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        filename = get_filename_from_url(get_url(environ)) or "index.html"

        return send_from_directory(f"{paths.web_dir}/htdocs/openapi/swagger-ui-3/", filename)(
            environ, start_response
        )


@contextlib.contextmanager
def ensure_authenticated(persist: bool = True) -> typing.Iterator[None]:
    session.session.persist_session = persist
    if session.session.user is None or isinstance(session.session.user, LoggedInNobody):
        # As a user we want the most specific error messages. Due to the errors being
        # generated at the start of the request, where it isn't clear if Checkmk or RESTAPI
        # will take the request, we need to store them and emit them to the user afterwards.
        if session.session.exc:
            raise session.session.exc
        raise MKAuthException("You need to be logged in to access this resource.")
    yield


class CheckmkRESTAPI(AbstractWSGIApp):
    def __init__(self, debug: bool = False) -> None:
        super().__init__(debug)
        # This intermediate data structure is necessary because `Rule`s can't contain anything
        # other than str anymore. Technically they could, but the typing is now fixed to str.
        self._endpoints: dict[str, AbstractWSGIApp] = {}
        self._url_map: Map | None = None
        self._rules: list[Rule] = []

    def _build_url_map(self) -> Map:
        self._endpoints.clear()
        self._rules[:] = []

        self.add_rule(
            ["/ui/", "/ui/<path:path>"],
            ServeSwaggerUI(prefix="/[^/]+/check_mk/api/[^/]+/ui"),
            "swagger-ui",
        )
        self.add_rule(
            ["/openapi-swagger-ui.yaml"],
            ServeSpec("swagger-ui", "yaml"),
            "swagger-ui-yaml",
        )
        self.add_rule(
            ["/openapi-swagger-ui.json"],
            ServeSpec("swagger-ui", "json"),
            "swagger-ui-json",
        )
        self.add_rule(
            ["/openapi-doc.yaml"],
            ServeSpec("doc", "yaml"),
            "doc-yaml",
        )
        self.add_rule(
            ["/openapi-doc.json"],
            ServeSpec("doc", "json"),
            "doc-json",
        )

        endpoint: Endpoint
        for endpoint in ENDPOINT_REGISTRY:
            if self.debug:
                # This helps us to make sure we can always generate a valid OpenAPI yaml file.
                _ = endpoint.to_operation_dict()

            self.add_rule(
                [endpoint.default_path],
                EndpointAdapter(endpoint),
                endpoint.ident,
                methods=[endpoint.method],
            )

        return Map([Submount("/<_site>/check_mk/api/<_version>/", [*self._rules])])

    def add_rule(
        self,
        path_entries: list[str],
        endpoint: AbstractWSGIApp,
        key: str,
        methods: typing.Sequence[HTTPMethod] | None = None,
    ) -> None:
        if methods is None:
            methods = ["get"]
        self._endpoints[key] = endpoint
        for path in path_entries:
            self._rules.append(Rule(path, methods=methods, endpoint=key))

    def _lookup_destination(self, environ: WSGIEnvironment) -> tuple[AbstractWSGIApp, PathArgs]:
        """Match the URL which is requested with the corresponding endpoint.

        The returning of the path variables should be considered a hack and should be removed
        once the call graph to the Endpoint class is properly refactored.
        """
        if self._url_map is None:
            # NOTE: This needs to be executed in a Request context because it depends on
            # the configuration
            self._url_map = self._build_url_map()

        urls = self._url_map.bind_to_environ(environ)
        result: tuple[str, PathArgs] = urls.match(return_rule=False)
        endpoint_ident, matched_path_args = result

        # Remove _site & _version (see Submount above), so the validators don't go crazy.
        path_args = {
            key: value
            for key, value in matched_path_args.items()
            if key not in ("_site", "_version")
        }

        return self._endpoints[endpoint_ident], path_args

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        response: WSGIApplication

        try:
            wsgi_endpoint, path_args = self._lookup_destination(environ)

            if isinstance(wsgi_endpoint, EndpointAdapter):
                g.endpoint = wsgi_endpoint.endpoint

            # This is an implicit dependency, as we only know the args at runtime, but the
            # function at setup-time.
            environ[ARGS_KEY] = path_args

            # Only the GUI will persist sessions. You can log into the REST API using GUI
            # credentials, but accessing the REST API will never touch the session store. We also
            # don't want to have cookies sent to the HTTP client whenever one is logged in using
            # the header methods.
            with ensure_authenticated(persist=False):
                return wsgi_endpoint(environ, start_response)

        except ProblemException as exc:
            response = exc.to_problem()

        except MKHTTPException as exc:
            assert isinstance(exc.status, int)
            response = problem(
                status=exc.status,
                title=http.client.responses[exc.status],
                detail=str(exc),
            )

        except RestAPIRequestGeneralException as exc:
            response = exc.to_problem()

        except RestAPIPermissionException as exc:
            response = crash_report_response(exc)

        except RestAPIResponseGeneralException as exc:
            response = crash_report_response(exc)

        except HTTPException as exc:
            assert isinstance(exc.code, int)
            response = problem(
                status=exc.code,
                title=http.client.responses[exc.code],
                detail=str(exc),
            )

        except MKException as exc:
            if self.debug:
                raise
            response = problem(
                status=EXCEPTION_STATUS.get(type(exc), 500),
                title="An exception occurred.",
                detail=str(exc),
            )

        except Exception as exc:
            if self.debug:
                raise
            response = crash_report_response(exc)

        return response(environ, start_response)


class APICrashReport(crash_reporting.ABCCrashReport):
    """API specific crash reporting class."""

    @classmethod
    def type(cls):
        return "rest_api"
