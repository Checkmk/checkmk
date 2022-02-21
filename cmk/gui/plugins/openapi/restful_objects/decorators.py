#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Decorators to expose API endpoints.

Decorating a function with `Endpoint` will result in a change of the SPEC object,
which then has to be dumped into the checkmk.yaml file.

"""
from __future__ import annotations

import functools
import hashlib
import http.client
import json
import typing
from types import FunctionType
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import apispec  # type: ignore[import]
import apispec.utils  # type: ignore[import]
from marshmallow import Schema, ValidationError
from marshmallow.schema import SchemaMeta
from werkzeug.datastructures import MultiDict
from werkzeug.http import parse_options_header
from werkzeug.utils import import_string

from cmk.utils import store

from cmk.gui import fields
from cmk.gui import http as cmk_http
from cmk.gui.globals import config, request
from cmk.gui.plugins.openapi.restful_objects.code_examples import code_samples
from cmk.gui.plugins.openapi.restful_objects.endpoint_registry import ENDPOINT_REGISTRY
from cmk.gui.plugins.openapi.restful_objects.parameters import (
    CONTENT_TYPE,
    ETAG_HEADER_PARAM,
    ETAG_IF_MATCH_HEADER,
)
from cmk.gui.plugins.openapi.restful_objects.params import path_parameters, to_openapi, to_schema
from cmk.gui.plugins.openapi.restful_objects.response_schemas import ApiError
from cmk.gui.plugins.openapi.restful_objects.specification import SPEC
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    ContentObject,
    EndpointTarget,
    ETagBehaviour,
    HTTPMethod,
    LinkRelation,
    LocationType,
    OpenAPIParameter,
    OpenAPITag,
    OperationSpecType,
    PathItem,
    RawParameter,
    ResponseType,
    SchemaParameter,
    StatusCodeInt,
)
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.watolib.activate_changes import (
    update_config_generation as activate_changes_update_config_generation,
)
from cmk.gui.watolib.git import do_git_commit

if typing.TYPE_CHECKING:
    from cmk.gui.wsgi.type_defs import WSGIApplication

_SEEN_ENDPOINTS: Set[FunctionType] = set()

T = TypeVar("T")

WrappedFunc = Callable[[typing.Mapping[str, Any]], cmk_http.Response]


class WrappedEndpoint:
    def __init__(
        self,
        endpoint: Endpoint,
        func: WrappedFunc,
    ) -> None:
        self.endpoint: typing.Final = endpoint
        self.path: typing.Final = endpoint.path
        self.func: typing.Final = func

    def __call__(self, param: typing.Mapping[str, Any]) -> cmk_http.Response:
        return self.func(param)


Version = str


def to_named_schema(fields_: Dict[str, fields.Field]) -> Type[Schema]:
    attrs: Dict[str, Any] = fields_.copy()
    attrs["Meta"] = type(
        "GeneratedMeta",
        (Schema.Meta,),
        {"register": True, "ordered": True},
    )
    _hash = hashlib.sha256()

    def _update(d_):
        for key, value in sorted(d_.items()):
            _hash.update(str(key).encode("utf-8"))
            if hasattr(value, "metadata"):
                _update(value.metadata)
            else:
                _hash.update(str(value).encode("utf-8"))

    _update(fields_)

    name = f"GeneratedSchema{_hash.hexdigest()}"
    schema_cls: Type[Schema] = type(name, (Schema,), attrs)
    return schema_cls


def coalesce_schemas(
    parameters: Sequence[Tuple[LocationType, Sequence[RawParameter]]],
) -> Sequence[SchemaParameter]:
    rv: List[SchemaParameter] = []
    for location, params in parameters:
        if not params:
            continue

        to_convert: Dict[str, fields.Field] = {}
        for param in params:
            if isinstance(param, SchemaMeta):
                rv.append({"in": location, "schema": param})
            else:
                to_convert.update(param)

        if to_convert:
            rv.append({"in": location, "schema": to_named_schema(to_convert)})

    return rv


def _path_item(
    status_code: int,
    description: str,
    content: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, OpenAPIParameter]] = None,
) -> PathItem:
    """Build a OpenAPI PathItem segment

    Examples:

        >>> _path_item(404, "Godot is still not here.")  # doctest: +ELLIPSIS
        {'description': 'Not Found: Godot is still not here.', 'content': ...}

        >>> _path_item(422, "What's this?")  # doctest: +ELLIPSIS
        {'description': "Unprocessable Entity: What's this?", 'content': ...}

    Args:
        status_code:
            A HTTP status code

        description:
            Description for the segment.

        content:
            A dictionary which has content-types as keys and dicts as values in
            the form of {'schema': <marshmallowschema>}

        headers:


    Returns:

    """
    response: PathItem = {"description": f"{http.client.responses[status_code]}: {description}"}
    if status_code >= 400 and content is None:
        content = {"application/problem+json": {"schema": ApiError}}
    if content is None:
        content = {}
    response["content"] = content
    if headers:
        response["headers"] = headers
    return response


def _from_multi_dict(multi_dict: MultiDict) -> Dict[str, Union[List[str], str]]:
    """Transform a MultiDict to a non-heterogenous dict

    Meaning: lists are lists and lists of lenght 1 are scalars.

    Examples:
        >>> _from_multi_dict(MultiDict([('a', '1'), ('a', '2'), ('c', '3')]))
        {'a': ['1', '2'], 'c': '3'}

    Args:
        multi_dict:
            A Werkzeug MultiDict instance.

    Returns:
        A dict.

    """
    ret = {}
    for key, values in multi_dict.to_dict(flat=False).items():
        if len(values) == 1:
            ret[key] = values[0]
        else:
            ret[key] = values
    return ret


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

        update_config_generation:
            Wether to generate a new configuration. All endpoints with methods other than `get`
            normally trigger a regeneration of the configuration. This can be turned off by
            setting `update_config_generation` to False.

        **options:
            Various keys which will be directly applied to the OpenAPI operation object.

    """

    def __init__(
        self,
        path: str,
        link_relation: LinkRelation,
        method: HTTPMethod = "get",
        content_type: str = "application/json",
        output_empty: bool = False,
        response_schema: Optional[RawParameter] = None,
        request_schema: Optional[RawParameter] = None,
        convert_response: bool = True,
        skip_locking: bool = False,
        path_params: Optional[Sequence[RawParameter]] = None,
        query_params: Optional[Sequence[RawParameter]] = None,
        header_params: Optional[Sequence[RawParameter]] = None,
        etag: Optional[ETagBehaviour] = None,
        status_descriptions: Optional[Dict[int, str]] = None,
        options: Optional[Dict[str, str]] = None,
        tag_group: Literal["Monitoring", "Setup", "Checkmk Internal"] = "Setup",
        blacklist_in: Optional[Sequence[EndpointTarget]] = None,
        additional_status_codes: Optional[Sequence[StatusCodeInt]] = None,
        valid_from: Optional[Version] = None,
        valid_until: Optional[Version] = None,
        update_config_generation: bool = True,
    ):
        self.path = path
        self.link_relation = link_relation
        self.method = method
        self.content_type = content_type
        self.output_empty = output_empty
        self.response_schema = response_schema
        self.convert_response = convert_response
        self.skip_locking = skip_locking
        self.request_schema = request_schema
        self.path_params = path_params
        self.query_params = query_params
        self.header_params = header_params
        self.etag = etag
        self.status_descriptions = status_descriptions if status_descriptions is not None else {}
        self.options: Dict[str, str] = options if options is not None else {}
        self.tag_group = tag_group
        self.blacklist_in: List[EndpointTarget] = self._list(blacklist_in)
        self.additional_status_codes = self._list(additional_status_codes)
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.update_config_generation = update_config_generation

        self.operation_id: str
        self.func: WrappedFunc
        self.wrapped: Callable[[typing.Mapping[str, Any]], WSGIApplication]

        self._expected_status_codes = self.additional_status_codes.copy()

        if content_type == "application/json":
            if self.response_schema is not None:
                self._expected_status_codes.append(200)  # ok
        else:
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
            self._expected_status_codes.append(200)  # ok

        if self.output_empty:
            self._expected_status_codes.append(204)  # no content

        if self.method in ("put", "post"):
            self._expected_status_codes.append(400)  # bad request
            self._expected_status_codes.append(415)  # unsupported media type

        if self.path_params:
            self._expected_status_codes.append(404)  # not found

        if self.query_params or self.request_schema:
            self._expected_status_codes.append(400)  # bad request

        if self.etag in ("input", "both"):
            self._expected_status_codes.append(412)  # precondition failed
            self._expected_status_codes.append(428)  # precondition required

        for status_code, _ in self.status_descriptions.items():
            if status_code not in self._expected_status_codes:
                raise RuntimeError(
                    f"Unexpected custom status description. "
                    f"Status code {status_code} not expected for endpoint: {method.upper()} {path}"
                )

    def __repr__(self):
        return f"<Endpoint {self.func.__module__}:{self.func.__name__}>"

    def _list(self, sequence: Optional[Sequence[T]]) -> List[T]:
        return list(sequence) if sequence is not None else []

    def __call__(self, func: WrappedFunc) -> WrappedEndpoint:
        """This is the real decorator.
        Returns:
        A wrapped function. The wrapper does input and output validation.
        """
        self.operation_id = func.__module__ + "." + func.__name__
        if self.method in ("get", "delete") and self.request_schema:
            raise ValueError(
                f"According to the OpenAPI 3 spec, consumers SHALL ignore request bodies on "
                f"{self.method.upper()!r}. Please use another request method for the endpont: "
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

        _verify_parameters(self.path, path_schema)

        def _mandatory_parameter_names(*_params):
            schema: Type[Schema]
            req = []
            for schema in _params:
                if not schema:
                    continue
                for name, field in schema().declared_fields.items():
                    if field.required:
                        req.append(field.attribute or name)
            return tuple(sorted(req))

        params = _mandatory_parameter_names(header_schema, path_schema, query_schema)

        # Call to see if a Rule can be constructed. Will throw an AttributeError if not possible.
        _ = self.default_path

        ENDPOINT_REGISTRY.add_endpoint(self, params)

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

    def _is_expected_content_type(self, content_type_header: Optional[str]) -> None:
        if content_type_header is None:
            raise ValueError(f"No content-type specified. Possible value is: {self.content_type}")

        content_type, options = parse_options_header(content_type_header)
        if content_type == self.content_type:
            # Content-Type is as expected.
            if (
                content_type == "application/json"
                and "charset" in options
                and options["charset"] is not None
            ):
                # but there are options
                if options["charset"].lower() != "utf-8":
                    # with a charset we don't understand
                    raise ValueError(
                        f"Character set {options['charset']!r} not supported "
                        f"for content-type {content_type!r}."
                    )
        else:
            raise ValueError(f"Content-Type {content_type!r} not supported for this endpoint.")

    def wrap_with_validation(
        self,
        request_schema: Optional[Type[Schema]],
        response_schema: Optional[Type[Schema]],
        header_schema: Optional[Type[Schema]],
        path_schema: Optional[Type[Schema]],
        query_schema: Optional[Type[Schema]],
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
        def _validating_wrapper(param: typing.Mapping[str, Any]) -> cmk_http.Response:
            # TODO: Better error messages, pointing to the location where variables are missing

            _params = dict(param)
            del param

            def _format_fields(_messages: Union[List, Dict]) -> str:
                if isinstance(_messages, list):
                    return ", ".join(_messages)
                if isinstance(_messages, dict):
                    return ", ".join(_messages.keys())
                return ""

            def _problem(exc_, status_code=400):
                if isinstance(exc_.messages, dict):
                    messages = exc_.messages
                else:
                    messages = {"exc": exc_.messages}
                return problem(
                    status=status_code,
                    title=http.client.responses[status_code],
                    detail=f"These fields have problems: {_format_fields(exc_.messages)}",
                    ext={"fields": messages},
                )

            if self.method in ("post", "put") and request.get_data(cache=True):
                try:
                    self._is_expected_content_type(request.content_type)
                except ValueError as exc:
                    return problem(
                        status=415,
                        detail=str(exc),
                        title="Content type not valid for this endpoint.",
                    )

            try:
                if path_schema:
                    _params.update(path_schema().load(_params))
            except ValidationError as exc:
                return _problem(exc, status_code=404)

            try:
                if query_schema:
                    _params.update(query_schema().load(_from_multi_dict(request.args)))

                if header_schema:
                    _params.update(header_schema().load(request.headers))

                if request_schema:
                    # Try to decode only when there is data. Decoding an empty string will fail.
                    if request.get_data(cache=True):
                        json_data = request.json or {}
                    else:
                        json_data = {}
                    _params["body"] = request_schema().load(json_data)
            except ValidationError as exc:
                return _problem(exc, status_code=400)

            if not request.accept_mimetypes:
                return problem(
                    status=406, title="Not Acceptable", detail="Please specify an Accept Header."
                )
            if not request.accept_mimetypes.best_match([self.content_type]):
                return problem(
                    status=406,
                    title="Not Acceptable",
                    detail="Can not send a response with the content type specified in the 'Accept' Header."
                    f" Accept Header: {request.accept_mimetypes}."
                    f" Supported content types: [{self.content_type}]",
                )

            # make pylint happy
            assert callable(self.func)

            if self.tag_group == "Setup" and not config.wato_enabled:
                return problem(
                    status=403,
                    title="Forbidden: WATO is disabled",
                    detail="This endpoint is currently disabled via the "
                    "'Disable remote configuration' option in 'Distributed Monitoring'. "
                    "You may be able to query the central site.",
                )

            try:
                response = self.func(_params)
            except ValidationError as exc:
                return _problem(exc, status_code=400)

            if self.output_empty and response.status_code < 400 and response.data:
                return problem(
                    status=500,
                    title="Unexpected data was sent.",
                    detail=(f"Endpoint {self.operation_id}\n" "This is a bug, please report."),
                    ext={"data_sent": str(response.data)},
                )

            if self.output_empty:
                response.content_type = ""

            if response.status_code not in self._expected_status_codes:
                return problem(
                    status=500,
                    title=f"Unexpected status code returned: {response.status_code}",
                    detail=(f"Endpoint {self.operation_id}\n" "This is a bug, please report."),
                    ext={"codes": self._expected_status_codes},
                )

            # We assume something has been modified and increase the config generation ID
            # by one. This is necessary to ensure a warning in the "Activate Changes" GUI
            # about there being new changes to activate can be given to the user.
            if (
                self.method != "get"
                and response.status_code < 300
                and self.update_config_generation
            ):
                # We assume no configuration change on GET and no configuration change on
                # non-ok responses.
                activate_changes_update_config_generation()
                if config.wato_use_git:
                    do_git_commit()

            if (
                self.content_type == "application/json"
                and response.status_code < 300
                and response_schema
                and response.data
            ):
                try:
                    data = json.loads(response.data.decode("utf-8"))
                except json.decoder.JSONDecodeError as exc:
                    return problem(
                        status=500,
                        title="Server was about to send invalid JSON data.",
                        detail="This is an error of the implementation.",
                        ext={
                            "errors": str(exc),
                            "orig": response.data,
                        },
                    )
                try:
                    outbound = response_schema().dump(data)
                except ValidationError as exc:
                    return problem(
                        status=500,
                        title="Server was about to send an invalid response.",
                        detail="This is an error of the implementation.",
                        ext={
                            "errors": exc.messages,
                            "orig": data,
                        },
                    )

                if self.convert_response:
                    response.set_data(json.dumps(outbound))

            response.freeze()
            return response

        def _wrap_with_wato_lock(func: WrappedFunc) -> WrappedFunc:
            # We need to lock the whole of the validation process, not just the function itself.
            # This is necessary, because sometimes validation logic loads values which trigger
            # a cache-load, which - without locking - could become inconsistent. This is obviously
            # a deeper problem of those components which needs to be fixed as well.
            @functools.wraps(func)
            def _wrapper(param: typing.Mapping[str, Any]) -> cmk_http.Response:
                if not self.skip_locking and self.method != "get":
                    with store.lock_checkmk_configuration():
                        response = func(param)
                else:
                    response = func(param)
                return response

            return _wrapper

        return _wrap_with_wato_lock(_validating_wrapper)

    @property
    def does_redirects(self):
        # created, moved permanently, found
        return any(code in self._expected_status_codes for code in [201, 301, 302])

    @property
    def ident(self):
        """Provide an identity for the Endpoint

        This can be used for keys in a dictionary, e.g. the ENDPOINT_REGISTRY."""
        return f"{self.method}:{self.default_path}:{self.content_type}"

    @property
    def default_path(self):
        replace = {}
        if self.path_params is not None:
            parameters = to_openapi(self.path_params, "path")
            for param in parameters:
                name = param["name"]
                replace[name] = f"<string:{name}>"
        try:
            path = self.path.format(**replace)
        except KeyError:
            raise AttributeError(
                f"Endpoint {self.path} has unspecified path parameters. " f"Specified: {replace}"
            )
        return path

    def make_url(self, parameter_values: Dict[str, Any]):
        return self.path.format(**parameter_values)

    def _path_item(
        self,
        status_code: int,
        description: str,
        content: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, OpenAPIParameter]] = None,
    ) -> PathItem:
        message = self.status_descriptions.get(status_code)
        if message is None:
            message = description
        return _path_item(status_code, message, content, headers)

    def to_operation_dict(self) -> OperationSpecType:
        """Generate the openapi spec part of this endpoint.

        The result needs to be added to the `apispec` instance manually.
        """
        assert self.func is not None, "This object must be used in a decorator environment."
        assert self.operation_id is not None, "This object must be used in a decorator environment."

        module_obj = import_string(self.func.__module__)

        response_headers: Dict[str, OpenAPIParameter] = {}
        content_type_header = to_openapi([CONTENT_TYPE], "header")[0]
        del content_type_header["in"]
        response_headers[content_type_header.pop("name")] = content_type_header

        if self.etag in ("output", "both"):
            etag_header = to_openapi([ETAG_HEADER_PARAM], "header")[0]
            del etag_header["in"]
            response_headers[etag_header.pop("name")] = etag_header

        responses: ResponseType = {}

        responses["406"] = self._path_item(406, "The requests accept headers can not be satisfied.")

        if 401 in self._expected_status_codes:
            responses["401"] = self._path_item(
                401, "The user is not authorized to do this request."
            )

        if self.tag_group == "Setup":
            responses["403"] = self._path_item(403, "Configuration via WATO is disabled.")
        if self.tag_group == "Checkmk Internal" and 403 in self._expected_status_codes:
            responses["403"] = self._path_item(
                403,
                "You have insufficient permissions for this operation.",
            )

        if 404 in self._expected_status_codes:
            responses["404"] = self._path_item(404, "The requested object has not been found.")

        if 422 in self._expected_status_codes:
            responses["422"] = self._path_item(422, "The request could not be processed.")

        if 423 in self._expected_status_codes:
            responses["423"] = self._path_item(423, "This resource is currently locked.")

        if 405 in self._expected_status_codes:
            responses["405"] = _path_item(
                405, "Method not allowed: This request is only allowed " "with other HTTP methods"
            )

        if 409 in self._expected_status_codes:
            responses["409"] = self._path_item(
                409,
                "The request is in conflict with the stored resource.",
            )

        if 415 in self._expected_status_codes:
            responses["415"] = self._path_item(415, "The submitted content-type is not supported.")

        if 302 in self._expected_status_codes:
            responses["302"] = self._path_item(
                302,
                "Either the resource has moved or has not yet completed. Please see this "
                "resource for further information.",
            )

        if 400 in self._expected_status_codes:
            responses["400"] = self._path_item(400, "Parameter or validation failure.")

        # We don't(!) support any endpoint without an output schema.
        # Just define one!
        if 200 in self._expected_status_codes:
            if self.response_schema:
                content: ContentObject
                content = {self.content_type: {"schema": self.response_schema}}
            elif self.content_type == "application/octet-stream" or self.content_type.startswith(
                "image/"
            ):
                content = {
                    self.content_type: {
                        "schema": {
                            "type": "string",
                            "format": "binary",
                        }
                    }
                }
            else:
                raise ValueError(f"Unknown content-type: {self.content_type} Please add condition.")
            responses["200"] = self._path_item(
                200,
                "The operation was done successfully.",
                content=content,
                headers=response_headers,
            )

        if 204 in self._expected_status_codes:
            responses["204"] = self._path_item(
                204, "Operation done successfully. No further output."
            )

        if 412 in self._expected_status_codes:
            responses["412"] = self._path_item(
                412,
                "The value of the If-Match header doesn't match the object's ETag.",
            )

        if 428 in self._expected_status_codes:
            responses["428"] = self._path_item(428, "The required If-Match header is missing.")

        docstring_name = _docstring_name(module_obj.__doc__)
        tag_obj: OpenAPITag = {
            "name": docstring_name,
            "x-displayName": docstring_name,
        }
        docstring_desc = _docstring_description(module_obj.__doc__)
        if docstring_desc:
            tag_obj["description"] = docstring_desc
        _add_tag(tag_obj, tag_group=self.tag_group)

        operation_spec: OperationSpecType = {
            "operationId": self.operation_id,
            "tags": [docstring_name],
            "description": "",
        }

        header_params: List[RawParameter] = []
        query_params: Sequence[RawParameter] = (
            self.query_params if self.query_params is not None else []
        )
        path_params: Sequence[RawParameter] = (
            self.path_params if self.path_params is not None else []
        )

        if config.rest_api_etag_locking and self.etag in ("input", "both"):
            header_params.append(ETAG_IF_MATCH_HEADER)

        if self.request_schema:
            header_params.append(CONTENT_TYPE)

        # While we define the parameters separately to be able to use them for validation, the
        # OpenAPI spec expects them to be listed in on place, so here we bunch them together.
        operation_spec["parameters"] = coalesce_schemas(
            [
                ("header", header_params),
                ("query", query_params),
                ("path", path_params),
            ]
        )

        operation_spec["responses"] = responses

        if self.request_schema is not None:
            operation_spec["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": self.request_schema,
                    }
                },
            }

        operation_spec["x-codeSamples"] = code_samples(
            self,
            header_params=header_params,
            path_params=path_params,
            query_params=query_params,
        )

        # If we don't have any parameters we remove the empty list, so the spec will not have it.
        if not operation_spec["parameters"]:
            del operation_spec["parameters"]

        try:
            docstring_name = _docstring_name(self.func.__doc__)
        except ValueError as exc:
            raise ValueError(
                f"Function {module_obj.__name__}:{self.func.__name__} has no docstring."
            ) from exc

        if docstring_name:
            operation_spec["summary"] = docstring_name
        else:
            raise RuntimeError(f"Please put a docstring onto {self.operation_id}")
        docstring_desc = _docstring_description(self.func.__doc__)
        if docstring_desc:
            operation_spec["description"] = docstring_desc

        apispec.utils.deepupdate(operation_spec, self.options)

        return {self.method: operation_spec}  # type: ignore[misc]


def _verify_parameters(
    path: str,
    path_schema: Optional[Type[Schema]],
):
    """Verifies matching of parameters to the placeholders used in an URL-Template

    This works both ways, ensuring that no parameter is supplied which is then not used and that
    each template-variable in the URL-template has a corresponding parameter supplied,
    either globally or locally.

    Args:
        path:
            The URL-Template, for eample: '/user/{username}'

        path_schema:
            A marshmallow schema which is used for path parameter validation.

    Examples:

        In case of success, this function will return nothing.

          >>> from cmk.fields import String
          >>> class Params(Schema):
          ...      bar = String()

          >>> _verify_parameters('/foo/{bar}', Params)
          >>> _verify_parameters('/foo', None)

        Yet, when problems are found, ValueErrors are raised.

          >>> _verify_parameters('/foo', Params)
          Traceback (most recent call last):
          ...
          ValueError: Params {'bar'} not used in path /foo. Found params: set()

          >>> _verify_parameters('/foo/{bar}', None)
          Traceback (most recent call last):
          ...
          ValueError: Params {'bar'} of path /foo/{bar} were not given in schema parameters set()

    Returns:
        Nothing.

    Raises:
        ValueError in case of a mismatch.

    """
    if path_schema is None:
        schema_params = set()
    else:
        schema = path_schema()
        schema_params = set(schema.declared_fields.keys())

    path_params = set(path_parameters(path))
    missing_in_schema = path_params - schema_params
    missing_in_path = schema_params - path_params

    if missing_in_schema:
        raise ValueError(
            f"Params {missing_in_schema!r} of path {path} were not given in schema parameters "
            f"{schema_params!r}"
        )

    if missing_in_path:
        raise ValueError(
            f"Params {missing_in_path!r} not used in path {path}. " f"Found params: {path_params!r}"
        )


def _assign_to_tag_group(tag_group: str, name: str) -> None:
    for group in SPEC.options.setdefault("x-tagGroups", []):
        if group["name"] == tag_group:
            group["tags"].append(name)
            break
    else:
        raise ValueError(f"x-tagGroup {tag_group} not found. Please add it to specification.py")


def _add_tag(tag: OpenAPITag, tag_group: Optional[str] = None) -> None:
    name = tag["name"]
    if name in [t["name"] for t in SPEC._tags]:
        return

    SPEC.tag(tag)
    if tag_group is not None:
        _assign_to_tag_group(tag_group, name)


def _schema_name(schema_name: str):
    """Remove the suffix 'Schema' from a schema-name.

    Examples:

        >>> _schema_name("BakeSchema")
        'Bake'

        >>> _schema_name("BakeSchemaa")
        'BakeSchemaa'

    Args:
        schema_name:
            The name of the Schema.

    Returns:
        The name of the Schema, maybe stripped of the suffix 'Schema'.

    """
    return schema_name[:-6] if schema_name.endswith("Schema") else schema_name


def _schema_definition(schema_name: str):
    ref = f"#/components/schemas/{_schema_name(schema_name)}"
    return f'<SchemaDefinition schemaRef="{ref}" showReadOnly={{true}} showWriteOnly={{true}} />'


def _tag_from_schema(schema: Type[Schema]) -> OpenAPITag:
    """Construct a Tag-Dict from a Schema instance or class

    Examples:

        >>> from marshmallow import Schema, fields

        >>> class TestSchema(Schema):
        ...      '''My docstring title.\\n\\nMore docstring.'''
        ...      field = fields.String()

        >>> expected = {
        ...    'x-displayName': 'My docstring title.',
        ...    'description': ('More docstring.\\n\\n'
        ...                    '<SchemaDefinition schemaRef="#/components/schemas/Test" '
        ...                    'showReadOnly={true} showWriteOnly={true} />'),
        ...    'name': 'Test'
        ... }

        >>> tag = _tag_from_schema(TestSchema)
        >>> assert tag == expected, tag

    Args:
        schema (marshmallow.Schema):
            A marshmallow Schema class or instance.

    Returns:
        A dict containing the tag name and the description, which is taken from

    """
    tag: OpenAPITag = {"name": _schema_name(schema.__name__)}
    docstring_name = _docstring_name(schema.__doc__)
    if docstring_name:
        tag["x-displayName"] = docstring_name
    docstring_desc = _docstring_description(schema.__doc__)
    if docstring_desc:
        tag["description"] = docstring_desc

    tag["description"] = tag.get("description", "")
    if tag["description"]:
        tag["description"] += "\n\n"
    tag["description"] += _schema_definition(schema.__name__)

    return tag


def _docstring_name(docstring: Optional[str]) -> str:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_name(_docstring_name.__doc__)
    'Split the docstring by title and rest.'

    >>> _docstring_name("")
    Traceback (most recent call last):
    ...
    ValueError: No name for the module defined. Please add a docstring!

    Args:
        docstring:

    Returns:
        A string or nothing.

    """ ""
    if not docstring:
        raise ValueError("No name for the module defined. Please add a docstring!")

    return [part.strip() for part in apispec.utils.dedent(docstring).split("\n\n", 1)][0]


def _docstring_description(docstring: Optional[str]) -> Optional[str]:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_description(_docstring_description.__doc__).split("\\n")[0]
    'This is part of the rest.'

    Args:
        docstring:

    Returns:
        A string or nothing.

    """
    if not docstring:
        return None
    parts = apispec.utils.dedent(docstring).split("\n\n", 1)
    if len(parts) > 1:
        return parts[1].strip()
    return None
