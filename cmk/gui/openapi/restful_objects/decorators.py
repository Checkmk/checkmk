#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Decorators to expose API endpoints.

Decorating a function with `Endpoint` will result in a change of the SPEC object,
which then has to be dumped into the checkmk.yaml file.

"""

from __future__ import annotations

import contextlib
import functools
import http.client
import json
import logging
import warnings
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any, Final, TypeVar

from marshmallow import Schema, ValidationError
from werkzeug.http import parse_options_header

from cmk.ccc import store
from cmk.ccc.version import Edition

from cmk.utils.paths import configuration_lockfile

from cmk.gui import hooks
from cmk.gui import http as cmk_http
from cmk.gui.config import active_config
from cmk.gui.http import HTTPMethod, request
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.permission_tracking import (
    enable_permission_tracking,
    is_permission_tracking_enabled,
)
from cmk.gui.openapi.restful_objects.api_error import ApiError
from cmk.gui.openapi.restful_objects.parameters import CONTENT_TYPE
from cmk.gui.openapi.restful_objects.params import to_schema
from cmk.gui.openapi.restful_objects.type_defs import (
    AcceptFieldType,
    EndpointTarget,
    ErrorStatusCodeInt,
    ETagBehaviour,
    LinkRelation,
    RawParameter,
    StatusCodeInt,
    TagGroup,
)
from cmk.gui.openapi.restful_objects.utils import (
    endpoint_ident,
    format_to_routing_path,
    identify_expected_status_codes,
)
from cmk.gui.openapi.restful_objects.validators import (
    ContentTypeValidator,
    HeaderValidator,
    PathParamsValidator,
    QueryParamsValidator,
    RequestDataValidator,
    ResponseValidator,
)
from cmk.gui.openapi.utils import (
    FIELDS,
    problem,
    ProblemException,
    RestAPIPermissionException,
    RestAPIWatoDisabledException,
)
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.activate_changes import (
    update_config_generation as activate_changes_update_config_generation,
)
from cmk.gui.watolib.git import do_git_commit

from cmk import trace

tracer = trace.get_tracer()
_logger = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

Version = str
WrappedFunc = Callable[[Mapping[str, Any]], cmk_http.Response]


class WrappedEndpoint:
    def __init__(
        self,
        endpoint: Endpoint,
        func: WrappedFunc,
    ) -> None:
        self.endpoint: Final = endpoint
        self.path: Final = endpoint.path
        self.func: Final = func

    def __call__(self, param: Mapping[str, Any]) -> cmk_http.Response:
        return self.func(param)


class Endpoint:
    """Mark the function as a REST-API endpoint.

    Notes:
        This decorator populates a global `apispec.APISpec` instance, so in order to have every
        possible endpoint in the resulting spec-file all of the endpoints have to be imported
        before reading out the APISpec instance.

    Args:
        path:
            The URI. Can contain 0-N placeholders like this: /path/{placeholder1}/{placeholder2}.
            These variables have to be defined elsewhere first. See the {query,path,header}_params
            Arguments of this class.

        link_relation:
            The link relation of the endpoint. This relation is used to identify an endpoint
            for linking. This has to be unique in it's module.

        method:
            The HTTP method under which the endpoint should be accessible. Methods are written
            lowercase in the OpenAPI YAML-file, though both upper and lower-cased method-names
            are supported here.

        content_type:
            The content-type under which this endpoint shall be executed. Multiple endpoints may
            be defined for any one URL, but only one endpoint per url-content-type combination.

        output_empty:
            When set to `True`, no output will be sent to the client and the HTTP status code
            will be set to 204 (OK, no-content). No response validation will be done.

        error_schemas:
            A dictionary of error schemas. The keys are the HTTP status codes and the values
            are the schemas.

        response_schema:
            The Schema subclass with which to validate the HTTP response.

        request_schema:
            The Schema subclass with which to validate the HTTP request. This will not validate
            HTTP headers, or query parameters though. For validating query parameters use the
            `path_params`, `query_params` and `header_params` parameters.

        path_params:
            All parameters, which are expected to be present in the URL itself. The `path` needs to
            contain this parameters in form of placeholders like this: `{variable_name}`.

        query_params:
            All parameters which are expected to be present in the `query string`. If not present
            the parameters may be sent to the endpoint, but they will be filtered out.

        header_params:
            All parameters, which are expected via HTTP headers.

        skip_locking:
            When set to True, the decorator will not try to acquire a wato configuration lock,
            which can lead to higher performance of this particular endpoint. WARNING: Do not
            activate this flag when configuration files are changed by the endpoint! This exposes
            the data to potential race conditions. Use it for endpoints which trigger livestatus
            commands.

        convert_response:
            When set to True (default), then the HTTP response content will be generated by the
            marshmallow schema. If switched off, the data from the endpoint is taken 1:1 and sent
            to the user.

        etag:
            One of 'input', 'output', 'both'. When set to 'input' a valid ETag is required in
            the 'If-Match' request header. When set to 'output' a ETag is sent to the client
            with the 'ETag' response header. When set to 'both', it will act as if set to
            'input' and 'output' at the same time.

        permissions_required:
            A declaration of the permissions required by this endpoint. This needs to be
            exhaustive in the sense that any permission which MAY be used by this endpoint NEEDS
            to be declared here!

            WARNING
                Failing to do so will result in runtime exceptions when an *undeclared*
                permission is required in the code.

            The combinators "Any" and "All" can be used to express more complex cases. For example:

                AnyPerm([All([Perm("wato.edit"), Perm("wato.access")]), Perm("wato.godmode")])

            This expresses that the endpoint requires either "wato.godmode" or "wato.access"
            and "wato.edit" at them same time. The nesting can be arbitrarily deep. For no access
            at all, NoPerm() can be used. Import these helpers from the `permissions` package.

        permissions_description:
            All declared permissions are documented in the REST API documentation with their
            default description taken from the permission_registry. When you need a more
            descriptive permission description you can declare them with a dict.

            Example:

                {"wato.godmode": "You can do whatever you want!"}

        update_config_generation:
            Whether to generate a new configuration. All endpoints with methods other than `get`
            normally trigger a regeneration of the configuration. This can be turned off by
            setting `update_config_generation` to False.

        deprecated_urls:
            A map from deprecated URL to Werk ID. The given URLs will be rendered exactly like the
            non-deprecated Endpoint, yet marked as *deprecated*. Additionally, a warning is written
            into its documentation string, explaining the deprecation and a link to the Werk.
            The URLs need to start with a slash /

        sort:
            An integer to influence the ordering of the endpoints in the yaml file.

        accept:
            The content-type accepted by the endpoint.

        internal_user_only:
            If set to True, then this endpoint is only accesible via InternalToken authentication method

        family_name:
            The name of the family this endpoint belongs to. This is used to group endpoints in the
            OpenAPI spec. If not set, the endpoint will infer the spec information based on the
            endpoint's module (legacy).

        supported_editions:
            The list of editions this endpoint is supported for. If not set, the endpoint will be
            available for all editions. This is used to filter endpoints in the OpenAPI spec.

        removed_in_version:
            The starting (inclusive) version from which the endpoint will be no longer available
            in the REST-API. All subsequent REST API versions will also not include this
            endpoint.

    """

    def __init__(
        self,
        path: str,
        link_relation: LinkRelation,
        method: HTTPMethod = "get",
        content_type: str = "application/json",
        output_empty: bool = False,
        error_schemas: Mapping[ErrorStatusCodeInt, type[ApiError]] | None = None,
        response_schema: RawParameter | None = None,
        request_schema: type[Schema] | None = None,
        convert_response: bool = True,
        skip_locking: bool = False,
        path_params: Sequence[RawParameter] | None = None,
        query_params: Sequence[RawParameter] | None = None,
        header_params: Sequence[RawParameter] | None = None,
        etag: ETagBehaviour | None = None,
        status_descriptions: dict[StatusCodeInt, str] | None = None,
        tag_group: TagGroup = "Setup",
        blacklist_in: Sequence[EndpointTarget] | None = None,
        additional_status_codes: Sequence[StatusCodeInt] | None = None,
        permissions_required: permissions.BasePerm | None = None,  # will be permissions.NoPerm()
        permissions_description: Mapping[str, str] | None = None,
        valid_from: Version | None = None,
        valid_until: Version | None = None,
        deprecated_urls: Mapping[str, int] | None = None,
        update_config_generation: bool = True,
        sort: int = 0,
        accept: AcceptFieldType = "application/json",
        internal_user_only: bool = False,
        family_name: str | None = None,
        supported_editions: set[Edition] | None = None,
        removed_in_version: APIVersion | None = None,
    ):
        self.path = path
        self.link_relation = link_relation
        self.method = method
        self.content_type = content_type
        self.output_empty = output_empty
        self.response_schema = response_schema
        self.convert_response = convert_response
        self.skip_locking = skip_locking
        self.error_schemas = self._dict(error_schemas)
        self.request_schema = request_schema
        self.path_params = path_params
        self.query_params = query_params
        self.header_params = header_params
        self.etag = etag
        self.status_descriptions = self._dict(status_descriptions)
        self.tag_group = tag_group
        self.blacklist_in: list[EndpointTarget] = self._list(blacklist_in)
        self.permissions_description = self._dict(permissions_description)
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.sort = sort
        self.accept = accept if isinstance(accept, list) else [accept]
        self.internal_user_only = internal_user_only
        self.family_name = family_name
        self.supported_editions = supported_editions
        self.removed_in_version = removed_in_version

        if deprecated_urls is not None:
            for url in deprecated_urls:
                if not url.startswith("/"):
                    raise ValueError(f"Deprecated URL {url!r} doesn't start with a slash /.")
        self.deprecated_urls = deprecated_urls
        self.update_config_generation = update_config_generation

        self.operation_id: str
        self.func: WrappedFunc
        self.wrapped: Callable[[Mapping[str, Any]], cmk_http.Response]

        self.permissions_required = permissions_required
        self._used_permissions: set[str] = set()

        # TODO: should maintain set functionality
        self._expected_status_codes = list(
            identify_expected_status_codes(
                method=self.method,
                doc_category=self.tag_group,
                content_type=self.content_type,
                etag=self.etag,
                has_response=not output_empty,
                has_path_params=self.path_params is not None,
                has_query_params=self.query_params is not None,
                has_request_schema=self.request_schema is not None,
                additional_status_codes=self._list(additional_status_codes),
            )
        )

        if content_type != "application/json":
            if output_empty:
                raise ValueError(
                    f"output_emtpy=True not allowed on custom content_type "
                    f"{self.content_type}. [{self.method} {self.path}]"
                )
            if response_schema:
                raise ValueError(
                    "response_schema not allowed for content_type "
                    f"{self.content_type}. [{self.method} {self.path}]"
                )

        if self.method == "delete" and self.request_schema:
            warnings.warn(
                f"Endpoint {self} uses a body in a DELETE request. Even though the RFC does not "
                "disallow or discourage it, many HTTP clients have problems with DELETE requests "
                "containing bodies. Consider using the POST method instead.",
                UserWarning,
            )

        for error_status_code in self.error_schemas:
            if error_status_code < 400:
                raise RuntimeError(f"Error schema not allowed for status code {error_status_code}.")
            if error_status_code not in self._expected_status_codes:
                raise RuntimeError(
                    f"Error schema for status code {error_status_code} not allowed, due to it "
                    "not being in the expected status codes."
                )

        for status_code, _ in self.status_descriptions.items():
            if status_code not in self._expected_status_codes:
                raise RuntimeError(
                    "Unexpected custom status description. "
                    f"Status code {status_code} not expected for endpoint: {method.upper()} {path}"
                )

    def error_schema(self, status_code: ErrorStatusCodeInt) -> ApiError:
        schema: type[ApiError] = self.error_schemas.get(status_code, ApiError)
        return schema()

    @contextlib.contextmanager
    def register_permission_tracking(self) -> Iterator[None]:
        hooks.register_builtin("permission-checked", self._on_permission_checked)
        try:
            with enable_permission_tracking():
                yield
        finally:
            hooks.unregister("permission-checked", self._on_permission_checked)

    def _on_permission_checked(self, pname: str) -> None:
        """Collect all checked permissions during execution

        We need to remember this, in oder to later check if the set of required permissions
        actually fits the declared permission schema.
        """
        if not is_permission_tracking_enabled():
            return

        self.remember_checked_permission(pname)
        permission_not_declared = (
            self.permissions_required is not None and pname not in self.permissions_required
        )
        if permission_not_declared:
            _logger.error(
                "Permission mismatch: Endpoint %r Use of undeclared permission %s",
                self,
                pname,
            )

            if request.environ.get("paste.testing"):
                raise RestAPIPermissionException(
                    title=f"Required permissions ({pname}) not declared for this endpoint.",
                    detail=f"Endpoint: {self}\n"
                    f"Permission: {pname}\n"
                    f"Used permission: {self._used_permissions}\n"
                    f"Declared: {self.permissions_required}\n",
                )

    def remember_checked_permission(self, permission: str) -> None:
        """Remember that a permission has been required (used)

        The endpoint acts as a storage for triggered permissions under the current run. Once
        the request has been done, everything is forgotten again."""
        self._used_permissions.add(permission)

    def __repr__(self) -> str:
        return f"<Endpoint {self.func.__module__}:{self.func.__name__}>"

    def _list(self, sequence: Sequence[T] | None) -> list[T]:
        return list(sequence) if sequence is not None else []

    def _dict(self, mapping: Mapping[K, V] | None) -> dict[K, V]:
        return dict(mapping) if mapping is not None else {}

    def __call__(self, func: WrappedFunc) -> WrappedEndpoint:
        """This is the real decorator.
        Returns:
        A wrapped function. The wrapper does input and output validation.
        """
        self.operation_id = func.__module__ + "." + func.__name__
        if self.method in ("get", "delete") and self.request_schema:
            raise ValueError(
                f"According to the OpenAPI 3 spec, consumers SHALL ignore request bodies on "
                f"{self.method.upper()!r}. Please use another request method for the endpoint: "
                f"{self.operation_id} "
                "See: https://swagger.io/specification/#operation-object"
            )

        header_schema = None
        if self.header_params is not None:
            header_params = list(self.header_params)
            if self.request_schema:
                header_params.append(CONTENT_TYPE)
            header_schema = to_schema(header_params)

        path_schema = to_schema(self.path_params)
        query_schema = to_schema(self.query_params)
        response_schema = to_schema(self.response_schema)
        request_schema = to_schema(self.request_schema)

        self.func = func

        wrapped = self.wrapped = self.wrap_with_validation(
            request_schema,
            response_schema,
            header_schema,
            path_schema,
            query_schema,
        )

        PathParamsValidator.verify_marshmallow_params_presence(self.path, path_schema)

        # Call to see if a Rule can be constructed. Will throw an AttributeError if not possible.
        _ = self.default_path

        if (
            self.content_type == "application/json"
            and not self.output_empty
            and self.response_schema is None
        ):
            raise ValueError(
                f"{self.operation_id}: 'response_schema' required when output will be sent."
            )

        if self.output_empty and self.response_schema:
            raise ValueError(
                f"{self.operation_id}: If `output_empty` is True, "
                "'response_schema' may not be used."
            )

        return WrappedEndpoint(self, wrapped)

    def _format_fields(self, _messages: list | dict) -> str:
        if isinstance(_messages, list):
            return ", ".join(_messages)
        return ", ".join(_messages.keys())

    def _content_type_validation(self) -> None:
        ContentTypeValidator.validate(
            has_schema=self.request_schema is not None,
            content_type=request.content_type,
            accepted_types=self.accept,
            method=self.method,
        )

    def _path_validation(self, path_schema: type[Schema] | None, _params: dict[str, Any]) -> None:
        if path_schema is None:
            return

        with tracer.span("path-parameter-validation"):
            validated_path_params = PathParamsValidator.validate_marshmallow_schema(
                path_schema,
                _params,
            )
            _params.update(validated_path_params)

    def _query_param_validation(
        self, query_schema: type[Schema] | None, _params: dict[str, Any]
    ) -> None:
        if query_schema is None:
            return

        with tracer.span("query-parameter-validation"):
            validated_query_params = QueryParamsValidator.validate_marshmallow_schema(
                query_schema,
                request.args,
            )
            _params.update(validated_query_params)

    def _header_validation(
        self, header_schema: type[Schema] | None, _params: dict[str, Any]
    ) -> None:
        if header_schema:
            with tracer.span("header-parameter-validation"):
                validated_headers = HeaderValidator.validate_marshmallow_schema(
                    header_schema,
                    dict(request.headers),
                )
                _params.update(validated_headers)

        HeaderValidator.validate_accept_header(self.content_type, request.accept_mimetypes)

    def _request_data_validation(
        self, request_schema: type[Schema] | None, _params: dict[str, Any]
    ) -> None:
        # request.content_type was previously validated and is accepted by the endpoint or is None.
        # If there is content_type, then we try to decode the payload
        content_type, _ = parse_options_header(request.content_type)

        if content_type:
            with tracer.span("request-body-validation"):
                body = RequestDataValidator.decode_marshmallow_schema(
                    content_type=content_type,
                    request_obj=request,
                    request_schema=request_schema,
                )
                if body is not None:
                    _params["body"] = body
                    _params["content_type"] = content_type

    def _validate_response(
        self, response_schema: type[Schema] | None, _params: dict[str, Any]
    ) -> cmk_http.Response:
        with tracer.span("endpoint-body-call"):
            try:
                response = self.func(_params)
            except ValidationError as exc:
                response = problem(
                    status=400,
                    title=http.client.responses[400],
                    detail=f"These fields have problems: {self._format_fields(exc.messages)}",
                    fields=FIELDS(
                        exc.messages if isinstance(exc.messages, dict) else {"exc": exc.messages},
                    ),
                )
            except ProblemException as problem_exception:
                response = problem_exception.to_problem()

        # We don't expect a permission to be triggered when an endpoint ran into an error.
        if response.status_code < 400:
            is_testing_context = bool(request.environ.get("paste.testing", "False"))
            assert isinstance(is_testing_context, bool)

            ResponseValidator.validate_permissions(
                endpoint=str(self),
                params=_params,
                permissions_required=self.permissions_required,
                used_permissions=self._used_permissions,
                is_testing=is_testing_context,
            )

        ResponseValidator.validate_response_constraints(
            response=response,
            output_empty=self.output_empty,
            operation_id=self.operation_id,
            # TODO: should be a set
            expected_status_codes=self._expected_status_codes,
        )

        # We assume something has been modified and increase the config generation ID
        # by one. This is necessary to ensure a warning in the "Activate Changes" GUI
        # about there being new changes to activate can be given to the user.
        if self.method != "get" and response.status_code < 300 and self.update_config_generation:
            # We assume no configuration change on GET and no configuration change on
            # non-ok responses.
            activate_changes_update_config_generation()
            if active_config.wato_use_git:
                do_git_commit()

        if (
            self.content_type == "application/json"
            and response.status_code < 300
            and response_schema
            and response.data
        ):
            outbound = ResponseValidator.validate_marshmallow_schema(
                response=response,
                response_schema=response_schema,
            )

            if self.convert_response:
                with tracer.span("json-to-response"):
                    response.set_data(json.dumps(outbound))

        elif response.headers.get("Content-Type") == "application/problem+json" and response.data:
            ResponseValidator.validate_problem_json(response)

        response.freeze()
        # response code 204 does not have headers.
        if response.status_code == 204:
            for key in ["Content-Type", "Etag"]:
                del response.headers[key]
        return response

    def wrap_with_validation(
        self,
        request_schema: type[Schema] | None,
        response_schema: type[Schema] | None,
        header_schema: type[Schema] | None,
        path_schema: type[Schema] | None,
        query_schema: type[Schema] | None,
    ) -> WrappedFunc:
        """Wrap a function with schema validation logic.

        Args:
            request_schema:
                Optionally, a schema to validate the JSON request body.

            response_schema:
                Optionally, a schema to validate the response body.

            header_schema:
                Optionally, as schema to validate the HTTP headers.

            path_schema:
                Optionally, as schema to validate the path template variables.

            query_schema:
                Optionally, as schema to validate the query string parameters.

        Returns:
            The wrapping function.
        """
        if self.func is None:
            raise RuntimeError("Decorating failure. function not set.")

        @functools.wraps(self.func)
        def _validating_wrapper(param: Mapping[str, Any]) -> cmk_http.Response:
            # TODO: Better error messages, pointing to the location where variables are missing

            self._used_permissions = set()

            _params = dict(param)
            del param

            self._content_type_validation()
            self._path_validation(path_schema, _params)
            self._query_param_validation(query_schema, _params)
            self._header_validation(header_schema, _params)
            self._request_data_validation(request_schema, _params)

            # make pylint happy
            assert callable(self.func)

            if self.tag_group == "Setup" and not active_config.wato_enabled:
                raise RestAPIWatoDisabledException(
                    title="Forbidden: Setup is disabled",
                    detail="This endpoint is currently disabled via the "
                    "'Disable remote configuration' option in 'Distributed Monitoring'. "
                    "You may be able to query the central site.",
                )

            # TODO: Uncomment in later commit
            # if self.permissions_required is None:
            #     # Intentionally generate a crash report.
            #     raise PermissionError(f"Permissions need to be specified for {self}")

            return self._validate_response(response_schema, _params)

        def _wrap_with_wato_lock(func: WrappedFunc) -> WrappedFunc:
            # We need to lock the whole of the validation process, not just the function itself.
            # This is necessary, because sometimes validation logic loads values which trigger
            # a cache-load, which - without locking - could become inconsistent. This is obviously
            # a deeper problem of those components which needs to be fixed as well.
            @functools.wraps(func)
            def _wrapper(param: Mapping[str, Any]) -> cmk_http.Response:
                if not self.skip_locking and self.method != "get":
                    with store.lock_checkmk_configuration(configuration_lockfile):
                        response = func(param)
                else:
                    response = func(param)
                return response

            return _wrapper

        return _wrap_with_wato_lock(_validating_wrapper)

    @property
    def expected_status_codes(self) -> Sequence[StatusCodeInt]:
        return self._expected_status_codes

    @property
    def does_redirects(self):
        # created, moved permanently, found, see other
        return any(code in self._expected_status_codes for code in [201, 301, 302, 303])

    @property
    def ident(self) -> str:
        return endpoint_ident(
            method=self.method, route_path=self.default_path, content_type=self.content_type
        )

    @property
    def default_path(self) -> str:
        return format_to_routing_path(self.path)

    def make_url(self, parameter_values: dict[str, Any]) -> str:
        return self.path.format(**parameter_values)
