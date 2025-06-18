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
from collections.abc import Callable, Mapping
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, NotRequired, TYPE_CHECKING, TypedDict
from wsgiref.types import StartResponse, WSGIApplication, WSGIEnvironment

from apispec.yaml_utils import dict_to_yaml
from flask import g, send_from_directory
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule, Submount

import cmk.ccc.version as cmk_version
from cmk.ccc import crash_reporting, store
from cmk.ccc.exceptions import MKException
from cmk.ccc.site import omd_site, SiteId

from cmk.utils import paths

from cmk.gui import session
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKHTTPException, MKUserError
from cmk.gui.http import request, Response
from cmk.gui.logged_in import LoggedInNobody, LoggedInSuperUser, user
from cmk.gui.openapi.framework import ApiContext, RawRequestData
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.handler import handle_endpoint_request
from cmk.gui.openapi.framework.model.headers import (
    HEADER_CHECKMK_EDITION,
    HEADER_CHECKMK_VERSION,
)
from cmk.gui.openapi.framework.registry import EndpointDefinition
from cmk.gui.openapi.restful_objects import Endpoint
from cmk.gui.openapi.restful_objects.utils import format_to_routing_path
from cmk.gui.openapi.restful_objects.validators import PermissionValidator
from cmk.gui.openapi.restful_objects.versioned_endpoint_map import (
    discover_endpoints,
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

type EndpointIdent = str


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


def _add_checkmk_headers(response: Response) -> None:
    """Add Checkmk headers to the response.

    Adds the Checkmk version and edition to the response headers.
    """
    response.headers[HEADER_CHECKMK_VERSION["name"]] = cmk_version.__version__
    response.headers[HEADER_CHECKMK_EDITION["name"]] = cmk_version.edition(paths.omd_root).short


class VersionedEndpointAdapter(AbstractWSGIApp):
    """Wrap an EndpointDefinition

    Makes a "real" WSGI application out of a versioned definition.
    """

    __slots__ = ("endpoint", "requested_version")

    def __init__(
        self, endpoint: EndpointDefinition, requested_version: APIVersion, debug: bool = False
    ) -> None:
        super().__init__(debug)
        self.endpoint = endpoint
        self.requested_version = requested_version

    def __repr__(self) -> str:
        return f"<VersionedEndpointAdapter {self.endpoint.metadata.method} {self.endpoint.metadata.path}>"

    @staticmethod
    def _query_args() -> dict[str, list[str]]:
        query_args = request.args
        return {key: query_args.getlist(key) for key in query_args}

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        path_args = environ[ARGS_KEY]
        request_data: RawRequestData = {
            "body": request.data,
            "path": path_args,
            "query": self._query_args(),
            "headers": request.headers,
        }

        is_testing = str(request.environ.get("paste.testing", "False")).lower() == "true"

        # Create the response
        permission_validator = PermissionValidator.create(
            required_permissions=self.endpoint.permissions.required,
            endpoint_repr=self.endpoint.ident,
            is_testing=is_testing,
        )
        response = handle_endpoint_request(
            endpoint=self.endpoint.request_endpoint(),
            request_data=request_data,
            api_context=ApiContext(version=self.requested_version),
            permission_validator=permission_validator,
            wato_enabled=active_config.wato_enabled,
            wato_use_git=active_config.wato_use_git,
            is_testing=is_testing,
        )
        _add_checkmk_headers(response)

        # Serve the response
        return response(environ, start_response)


class LegacyEndpointAdapter(AbstractWSGIApp):
    """Wrap an Endpoint

    Makes a "real" WSGI application out of an endpoint. Should be refactored away.
    """

    __slots__ = ("endpoint",)

    def __init__(self, endpoint: Endpoint, debug: bool = False) -> None:
        super().__init__(debug)
        self.endpoint = endpoint

    def __repr__(self) -> str:
        return f"<LegacyEndpointAdapter {self.endpoint!r}>"

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        path_args = environ[ARGS_KEY]

        # Create the response
        with self.endpoint.register_permission_tracking():
            wsgi_app: Response = self.endpoint.wrapped(ParameterDict(path_args))

        _add_checkmk_headers(wsgi_app)

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
    __slots__ = ("target", "extension")

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
    __slots__ = ("prefix", "data")

    def __init__(self, prefix: str = "", debug: bool = False) -> None:
        super().__init__(debug)
        self.prefix = prefix
        self.data: dict[str, Any] | None = None

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        filename = get_filename_from_url(get_url(environ)) or "index.html"

        return send_from_directory(paths.web_dir / "htdocs/openapi/swagger-ui-5.20.6", filename)(
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


type AdaptedEndpointMapByVersion = dict[APIVersion, dict[EndpointIdent, AbstractWSGIApp]]

type RulesByVersion = dict[APIVersion, list[Rule]]

type MapByVersion = dict[APIVersion, Map]


class CheckmkRESTAPI(AbstractWSGIApp):
    __slots__ = ("_versioned_url_map", "_versioned_endpoints", "_versioned_rules", "testing")

    def __init__(self, debug: bool = False, testing: bool = False) -> None:
        super().__init__(debug)
        # This intermediate data structure is necessary because `Rule`s can't contain anything
        # other than str anymore. Technically they could, but the typing is now fixed to str.

        self._versioned_url_map: MapByVersion = {}
        self._versioned_endpoints: AdaptedEndpointMapByVersion = {}
        self._versioned_rules: RulesByVersion = {}

        self.testing = testing

        # with tracer.span("Build versioned URL map on CheckmkRESTAPI init"):
        #     self._url_map = self._build_versioned_url_map()

    def _build_versioned_url_map(self, version: APIVersion) -> Map:
        self._versioned_endpoints[version] = {}
        self._versioned_rules[version] = []

        with tracer.span(f"Building versioned rules for version {version}"):
            with tracer.span("Discovering endpoints"):
                endpoints = discover_endpoints(version)

            with tracer.span("Building routes"):
                for endpoint in endpoints.values():
                    if isinstance(endpoint, Endpoint):
                        legacy_endpoint = LegacyEndpointAdapter(endpoint)
                        self._add_versioned_rule(
                            path_entries=[legacy_endpoint.endpoint.default_path],
                            endpoint=legacy_endpoint,
                            method=legacy_endpoint.endpoint.method,
                            content_type=legacy_endpoint.endpoint.content_type,
                            version=version,
                        )

                    else:
                        versioned_endpoint = VersionedEndpointAdapter(
                            endpoint, requested_version=version
                        )
                        self._add_versioned_rule(
                            path_entries=[
                                format_to_routing_path(versioned_endpoint.endpoint.metadata.path)
                            ],
                            endpoint=versioned_endpoint,
                            method=versioned_endpoint.endpoint.metadata.method,
                            content_type=versioned_endpoint.endpoint.metadata.content_type,
                            version=version,
                        )

            with tracer.span("Adding documentation rules"):
                # TODO: These rules are from legacy. Need update to versioned
                self._add_versioned_rule(
                    path_entries=["/openapi-swagger-ui.yaml"],
                    endpoint=ServeSpec("swagger-ui", "yaml"),
                    content_type="application/yaml",
                    version=version,
                )
                self._add_versioned_rule(
                    path_entries=["/openapi-swagger-ui.json"],
                    endpoint=ServeSpec("swagger-ui", "json"),
                    content_type="application/json",
                    version=version,
                )
                self._add_versioned_rule(
                    path_entries=["/openapi-doc.yaml"],
                    endpoint=ServeSpec("doc", "yaml"),
                    content_type="application/yaml",
                    version=version,
                )
                self._add_versioned_rule(
                    path_entries=["/openapi-doc.json"],
                    endpoint=ServeSpec("doc", "json"),
                    content_type="application/json",
                    version=version,
                )

                self._add_versioned_rule(
                    path_entries=["/ui/", "/ui/<path:path>"],
                    endpoint=ServeSwaggerUI(prefix="/[^/]+/check_mk/api/[^/]+/ui"),
                    content_type="text/html",
                    version=version,
                )
        with tracer.span("Mounting rules"):
            return Map([Submount("/<_site>/check_mk/api/", self._versioned_rules[version])])

    def _add_versioned_rule(
        self,
        path_entries: list[str],
        endpoint: AbstractWSGIApp,
        version: APIVersion,
        content_type: str | None,
        method: HTTPMethod | None = None,
    ) -> None:
        if method is None:
            method = "get"

        for path in path_entries:
            path = path.lstrip("/")
            key = f"{version.value}:{method}:{path}:{content_type}"

            self._versioned_rules[version].append(
                Rule(f"/{version.value}/{path}", methods=[method], endpoint=key)
            )
            self._versioned_endpoints[version][key] = endpoint

            if version == APIVersion.V1:
                # alias 1.0 to v1
                key = f"1.0:{method}:{path}:{content_type}"
                self._versioned_rules[version].append(
                    Rule(f"/1.0/{path}", methods=[method], endpoint=key)
                )
                self._versioned_endpoints[version][key] = endpoint

    @tracer.instrument("CheckmkRESTAPI._lookup_destination")
    def _lookup_destination(
        self, environ: WSGIEnvironment
    ) -> tuple[AbstractWSGIApp, PathArgs, APIVersion]:
        """Match the URL which is requested with the corresponding endpoint.

        The returning of the path variables should be considered a hack and should be removed
        once the call graph to the Endpoint class is properly refactored.
        """

        # example: /heute/check_mk/api/1.0/openapi-doc.yaml
        requested_version_str = environ.get("PATH_INFO", "").split("/")[4]

        try:
            # 1.0 is an alias of APIVersion.V1
            requested_version = (
                APIVersion.V1
                if requested_version_str == "1.0"
                else APIVersion.from_string(requested_version_str)
            )

        except ValueError:
            raise NotFound()

        if self._versioned_url_map.get(requested_version) is None:
            with tracer.span(f"Building url map for version {requested_version}"):
                self._versioned_url_map[requested_version] = self._build_versioned_url_map(
                    requested_version
                )

        with tracer.span("Bind to environment and parse URL"):
            urls = self._versioned_url_map[requested_version].bind_to_environ(environ)

            result: tuple[str, PathArgs] = urls.match(return_rule=False)
            endpoint_ident, matched_path_args = result

            # Remove _site (see Submount above), so the validators don't go crazy.
            path_args = {key: value for key, value in matched_path_args.items() if key != "_site"}

        return (
            self._versioned_endpoints[requested_version][endpoint_ident],
            path_args,
            requested_version,
        )

    def wsgi_app(self, environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        response: WSGIApplication

        try:
            wsgi_endpoint, path_args, _requested_version = self._lookup_destination(environ)

            if isinstance(wsgi_endpoint, LegacyEndpointAdapter):
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
                isinstance(wsgi_endpoint, LegacyEndpointAdapter)
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
