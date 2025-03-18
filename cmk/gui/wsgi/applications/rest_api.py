#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import http.client
import json
import logging
import traceback
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, NotRequired, TYPE_CHECKING, TypedDict
from wsgiref.types import StartResponse, WSGIApplication, WSGIEnvironment

from apispec.yaml_utils import dict_to_yaml
from flask import g, send_from_directory
from marshmallow import fields as ma_fields
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule, Submount

from livestatus import SiteId

import cmk.ccc.version as cmk_version
from cmk.ccc import crash_reporting, store
from cmk.ccc.exceptions import MKException
from cmk.ccc.site import omd_site

from cmk.utils import paths

from cmk.gui import session
from cmk.gui.exceptions import MKAuthException, MKHTTPException, MKUserError
from cmk.gui.http import request, Response
from cmk.gui.logged_in import LoggedInNobody, LoggedInSuperUser, user
from cmk.gui.openapi import endpoint_registry
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.parameters import (
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.openapi.spec.utils import spec_path
from cmk.gui.openapi.utils import (
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

from cmk import trace
from cmk.crypto import MKCryptoException

if TYPE_CHECKING:
    from cmk.gui.http import HTTPMethod
    from cmk.gui.openapi.restful_objects.type_defs import EndpointTarget
    from cmk.gui.wsgi.type_defs import WSGIResponse

tracer = trace.get_tracer()

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
    site = omd_site()
    details = RestAPIDetails(
        crash_report_url={},
        request_info=RequestInfo(
            method="missing",
            data_received="missing",
            headers={"accept": "missing", "content_type": "missing"},
        ),
        check_mk_info={},
    )

    if isinstance(exc, GeneralRestAPIException):
        details["rest_api_exception"] = RestAPIException(
            description=exc.description,
            detail=exc.detail,
            ext=exc.ext,
            fields=exc.fields,
        )

    details["request_info"] = RequestInfo(
        method=request.environ["REQUEST_METHOD"],
        data_received=request.json if request.data else "",
        headers={
            "accept": request.environ.get("HTTP_ACCEPT", "missing"),
            "content_type": request.environ.get("CONTENT_TYPE", "missing"),
        },
    )

    details["check_mk_info"] = {
        "site": site,
        "check_mk_user": {
            "user_id": user.id,
            "user_roles": user.role_ids,
            "authorized_sites": list(user.authorized_sites()),
        },
    }

    crash = APICrashReport(
        paths.crash_dir,
        APICrashReport.make_crash_info(
            cmk_version.get_general_version_infos(paths.omd_root), details
        ),
    )
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
        crash.crash_info["exc_traceback"] = traceback.format_exc().split("\n")  # type: ignore[typeddict-item]

    crash_msg = (
        exc.description
        if isinstance(exc, GeneralRestAPIException)
        else crash.crash_info["exc_value"]
    )

    return problem(
        status=500,
        title="Internal Server Error",
        detail=f"{crash.crash_info['exc_type']}: {crash_msg}. Crash report generated. Please submit.",
        ext=EXT(
            {
                **crash.crash_info,
                **{"time": datetime.fromtimestamp(float(crash.crash_info["time"])).isoformat()},
            }
        ),
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
        wsgi_app.headers[_get_header_name(HEADER_CHECKMK_EDITION)] = cmk_version.edition(
            paths.omd_root
        ).short

        # Serve the response
        return wsgi_app(environ, start_response)


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


def _serve_spec(
    target: EndpointTarget,
    url: str,
    extension: Literal["yaml", "json"],
) -> Response:
    match extension:
        case "yaml":
            content_type = "application/x-yaml; charset=utf-8"
        case "json":
            content_type = "application/json"

    response = Response(status=200)
    response.data = _serialize_spec_cached(target, url, extension)
    response.content_type = content_type
    response.freeze()
    return response


def _serialize_spec_cached(
    target: EndpointTarget,
    url: str,
    extension: Literal["yaml", "json"],
) -> str:
    spec_mtime = spec_path(target).stat().st_mtime
    url_hash = sha256(url.encode("utf-8")).hexdigest()
    cache_file = paths.tmp_dir / "rest_api" / "spec_cache" / f"{target}-{extension}-{url_hash}.spec"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        if cache_file.stat().st_mtime > spec_mtime:
            return cache_file.read_text()
    except FileNotFoundError:
        pass

    serialized = _serialize_spec(target, url, extension)
    cache_file.write_text(serialized)
    return serialized


def _serialize_spec(target: EndpointTarget, url: str, extension: Literal["yaml", "json"]) -> str:
    serialize: Callable[[dict[str, Any]], str]
    match extension:
        case "yaml":
            serialize = dict_to_yaml
        case "json":
            serialize = json.dumps
    return serialize(_add_site_server(_read_spec(target), omd_site(), url))


def _read_spec(target: EndpointTarget) -> dict[str, Any]:
    path = spec_path(target)
    spec = store.load_object_from_file(path, default={})
    if not spec:
        raise ValueError(f"Failed to load spec from {path}")
    return spec


def _add_site_server(spec: dict[str, Any], site: SiteId, url: str) -> dict[str, Any]:
    """Add the server URL to the spec

    This step needs to happen with the current request context at hand to
    be able to add the protocol and URL currently being used by the client
    """
    spec.setdefault("servers", [])
    add_once(
        spec["servers"],
        {
            "url": url,
            "description": f"Site: {site}",
        },
    )
    return spec


def add_once(coll: list[dict[str, Any]], to_add: dict[str, Any]) -> None:
    """Add an entry to a collection, only once.

    Examples:

        >>> l = []
        >>> add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

        >>> add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

    Args:
        coll:
        to_add:

    Returns:

    """
    if to_add in coll:
        return None

    coll.append(to_add)
    return None


class ServeSpec(AbstractWSGIApp):
    def __init__(
        self, target: EndpointTarget, extension: Literal["yaml", "json"], debug: bool = False
    ) -> None:
        super().__init__(debug)
        self.target = target
        self.extension = extension

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        def _url(_environ: WSGIEnvironment) -> str:
            return "/".join(get_url(_environ).split("/")[:-1])

        return _serve_spec(
            target=self.target,
            url=_url(environ),
            extension=self.extension,
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


def _ensure_authenticated() -> None:
    session.session.is_gui_session = False
    if session.session.user is None or isinstance(session.session.user, LoggedInNobody):
        # As a user we want the most specific error messages. Due to the errors being
        # generated at the start of the request, where it isn't clear if Checkmk or RESTAPI
        # will take the request, we need to store them and emit them to the user afterwards.
        if session.session.exc:
            raise session.session.exc
        raise MKAuthException("You need to be logged in to access this resource.")
    if session.session.two_factor_pending():
        raise MKAuthException("Two-factor authentication required.")


class CheckmkRESTAPI(AbstractWSGIApp):
    def __init__(self, debug: bool = False, testing: bool = False) -> None:
        super().__init__(debug)
        # This intermediate data structure is necessary because `Rule`s can't contain anything
        # other than str anymore. Technically they could, but the typing is now fixed to str.
        self._endpoints: dict[str, AbstractWSGIApp] = {}
        self._url_map: Map | None = None
        self._rules: list[Rule] = []
        self.testing = testing

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
        for endpoint in endpoint_registry:
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
        methods: Sequence[HTTPMethod] | None = None,
    ) -> None:
        if methods is None:
            methods = ["get"]
        self._endpoints[key] = endpoint
        for path in path_entries:
            self._rules.append(Rule(path, methods=methods, endpoint=key))

    @tracer.instrument("CheckmkRESTAPI._lookup_destination")
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
            _ensure_authenticated()

            # A Checmk Reserved endpoint can only be accessed with the site secret
            if (
                isinstance(wsgi_endpoint, EndpointAdapter)
                and wsgi_endpoint.endpoint.internal_user_only
                and not isinstance(session.session.user, LoggedInSuperUser)
            ):
                raise MKAuthException("This endpoint is reserved for Checkmk.")

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

        except (MKException, MKCryptoException) as exc:
            if self.debug and not self.testing:
                raise
            response = problem(
                status=EXCEPTION_STATUS.get(type(exc), 500),
                title="An exception occurred.",
                detail=str(exc),
            )

        except Exception as exc:
            if self.debug and not self.testing:
                raise
            response = crash_report_response(exc)

        return response(environ, start_response)


class RestAPIException(TypedDict):
    description: str
    detail: str
    ext: dict[str, Any] | None
    fields: dict[str, Any] | None


class RequestInfo(TypedDict):
    data_received: Any
    method: str
    headers: dict[str, Any]


class RestAPIDetails(TypedDict):
    crash_report_url: dict[str, Any]
    rest_api_exception: NotRequired[RestAPIException]
    request_info: RequestInfo
    check_mk_info: dict[str, Any]


class APICrashReport(crash_reporting.ABCCrashReport[RestAPIDetails]):
    """API specific crash reporting class."""

    @classmethod
    def type(cls):
        return "rest_api"
