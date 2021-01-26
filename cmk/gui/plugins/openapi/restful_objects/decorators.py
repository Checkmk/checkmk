#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Decorators to expose API endpoints.

Decorating a function with `Endpoint` will result in a change of the SPEC object,
which then has to be dumped into the checkmk.yaml file.

"""
import functools
import hashlib
from types import FunctionType
from typing import Any, Dict, List, Optional, Sequence, Set, Type, Union, Tuple, Literal

import apispec  # type: ignore[import]
import apispec.utils  # type: ignore[import]
from marshmallow import Schema, ValidationError
from marshmallow.schema import SchemaMeta
from werkzeug.utils import import_string

from cmk.gui.globals import request
from cmk.gui.plugins.openapi import fields
from cmk.gui.plugins.openapi.utils import problem
from cmk.gui.plugins.openapi.restful_objects.code_examples import code_samples
from cmk.gui.plugins.openapi.restful_objects.parameters import (
    ETAG_HEADER_PARAM,
    ETAG_IF_MATCH_HEADER,
)
from cmk.gui.plugins.openapi.restful_objects.params import path_parameters, to_schema, to_openapi
from cmk.gui.plugins.openapi.restful_objects.response_schemas import ApiError
from cmk.gui.plugins.openapi.restful_objects.specification import (
    SPEC,)
from cmk.gui.plugins.openapi.restful_objects.endpoint_registry import ENDPOINT_REGISTRY
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    EndpointName,
    ETagBehaviour,
    HTTPMethod,
    OpenAPIParameter,
    OpenAPITag,
    OperationSpecType,
    LocationType,
    RawParameter,
    ResponseType,
    SchemaParameter,
)

_SEEN_ENDPOINTS: Set[FunctionType] = set()


def to_named_schema(fields_: Dict[str, fields.Field]) -> Type[Schema]:
    attrs: Dict[str, Any] = fields_.copy()
    attrs["Meta"] = type(
        "GeneratedMeta",
        (Schema.Meta,),
        {
            "register": True,
            "ordered": True
        },
    )
    _hash = hashlib.sha256()

    def _update(d_):
        for key, value in sorted(d_.items()):
            _hash.update(str(key).encode('utf-8'))
            if hasattr(value, 'metadata'):
                _update(value.metadata)
            else:
                _hash.update(str(value).encode('utf-8'))

    _update(fields_)

    name = f"GeneratedSchema{_hash.hexdigest()}"
    schema_cls: Type[Schema] = type(name, (Schema,), attrs)
    return schema_cls


def coalesce_schemas(
    parameters: Sequence[Tuple[LocationType,
                               Sequence[RawParameter]]],) -> Sequence[SchemaParameter]:
    rv: List[SchemaParameter] = []
    for location, params in parameters:
        if not params:
            continue

        to_convert: Dict[str, fields.Field] = {}
        for param in params:
            if isinstance(param, SchemaMeta):
                rv.append({'in': location, 'schema': param})
            else:
                to_convert.update(param)

        if to_convert:
            rv.append({'in': location, 'schema': to_named_schema(to_convert)})

    return rv


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

        name:
            The name of the endpoint. This is the name where this endpoint is "registered" under
            and can only be used once globally.

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

        etag:
            One of 'input', 'output', 'both'. When set to 'input' a valid ETag is required in
            the 'If-Match' request header. When set to 'output' a ETag is sent to the client
            with the 'ETag' response header. When set to 'both', it will act as if set to
            'input' and 'output' at the same time.

        will_do_redirects:
            This endpoint can also emit a 302 response (moved temporarily) code. Setting this to
            true will add this to the specification and documentation. Defaults to False.

        **options:
            Various keys which will be directly applied to the OpenAPI operation object.

    """
    def __init__(
        self,
        path: str,
        name: EndpointName,
        method: HTTPMethod = 'get',
        content_type: str = 'application/json',
        output_empty: bool = False,
        response_schema: Optional[Type[Schema]] = None,
        request_schema: Optional[Type[Schema]] = None,
        path_params: Optional[Sequence[RawParameter]] = None,
        query_params: Optional[Sequence[RawParameter]] = None,
        header_params: Optional[Sequence[RawParameter]] = None,
        etag: Optional[ETagBehaviour] = None,
        will_do_redirects: bool = False,
        status_descriptions: Optional[Dict[int, str]] = None,
        options: Optional[Dict[str, str]] = None,
        tag_group: Literal['Monitoring', 'Setup'] = 'Setup',
        func: Optional[FunctionType] = None,
        operation_id: Optional[str] = None,
        wrapped: Optional[Any] = None,
    ):
        self.path = path
        self.name = name
        self.method = method
        self.content_type = content_type
        self.output_empty = output_empty
        self.response_schema = response_schema
        self.request_schema = request_schema
        self.path_params = path_params
        self.query_params = query_params
        self.header_params = header_params
        self.etag = etag
        self.will_do_redirects = will_do_redirects
        self.status_descriptions = status_descriptions if status_descriptions is not None else {}
        self.options: Dict[str, str] = options if options is not None else {}
        self.tag_group = tag_group
        self.func = func
        self.operation_id = operation_id
        self.wrapped = wrapped

    def __call__(self, func):
        """This is the real decorator.
        Returns:
        A wrapped function. The wrapper does input and output validation.
        """
        header_schema = to_schema(self.header_params)
        path_schema = to_schema(self.path_params, required='all')
        query_schema = to_schema(self.query_params)

        self.func = func

        wrapped = self.wrap_with_validation(
            self.request_schema,
            self.response_schema,
            header_schema,
            path_schema,
            query_schema,
        )

        _verify_parameters(self.path, path_schema)

        self.operation_id = func.__module__ + "." + func.__name__

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

        if not self.output_empty and self.response_schema is None:
            raise ValueError(
                f"{self.operation_id}: 'response_schema' required when output will be sent.")

        if self.output_empty and self.response_schema:
            raise ValueError(f"{self.operation_id}: If `output_empty` is True, "
                             "'response_schema' may not be used.")

        self.wrapped = wrapped
        return self.wrapped

    def wrap_with_validation(
        self,
        request_schema: Optional[Type[Schema]],
        response_schema: Optional[Type[Schema]],
        header_schema: Optional[Type[Schema]],
        path_schema: Optional[Type[Schema]],
        query_schema: Optional[Type[Schema]],
    ):
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
        def _validating_wrapper(param):
            # TODO: Better error messages, pointing to the location where variables are missing
            try:
                if path_schema:
                    param.update(path_schema().load(param))

                if query_schema:
                    param.update(query_schema().load(request.args))

                if header_schema:
                    param.update(header_schema().load(request.headers))

                if request_schema:
                    body = request_schema().load(request.json or {})
                    param['body'] = body
            except ValidationError as exc:

                def _format_fields(_messages: Union[List, Dict]) -> str:
                    if isinstance(_messages, list):
                        return ', '.join(_messages)
                    if isinstance(_messages, dict):
                        return ', '.join(_messages.keys())
                    return ''

                if isinstance(exc.messages, dict):
                    messages = exc.messages
                else:
                    messages = {'exc': exc.messages}
                return problem(
                    status=400,
                    title="Bad request.",
                    detail=f"These fields have problems: {_format_fields(exc.messages)}",
                    ext=messages,
                )

            # make pylint happy
            assert callable(self.func)
            # FIXME
            # We need to get the "original data" somewhere and are currently "piggy-backing"
            # it on the response instance. This is somewhat problematic because it's not
            # expected behaviour and not a valid interface of Response. Needs refactoring.
            response = self.func(param)
            if hasattr(response, 'original_data') and response_schema:
                try:
                    response_schema().load(response.original_data)
                    return response
                except ValidationError as exc:
                    # Hope we never get here in production.
                    return problem(
                        status=500,
                        title="Server was about to send an invalid response.",
                        detail="This is an error of the implementation.",
                        ext={
                            'errors': exc.messages,
                            'orig': response.original_data
                        },
                    )

            return response

        return _validating_wrapper

    @property
    def default_path(self):
        replace = {}
        if self.path_params is not None:
            parameters = to_openapi(self.path_params, 'path')
            for param in parameters:
                name = param['name']
                replace[name] = f"<string:{name}>"
        try:
            path = self.path.format(**replace)
        except KeyError:
            raise AttributeError(f"Endpoint {self.path} has unspecified path parameters. "
                                 f"Specified: {replace}")
        return path

    def make_url(self, parameter_values: Dict[str, Any]):
        return self.path.format(**parameter_values)

    def to_operation_dict(self) -> OperationSpecType:
        """Generate the openapi spec part of this endpoint.

        The result needs to be added to the `apispec` instance manually.
        """
        assert self.func is not None, "This object must be used in a decorator environment."
        assert self.operation_id is not None, "This object must be used in a decorator environment."

        module_obj = import_string(self.func.__module__)

        headers: Dict[str, OpenAPIParameter] = {}
        if self.etag in ('output', 'both'):
            etag_header = to_openapi([ETAG_HEADER_PARAM], 'header')[0]
            del etag_header['in']
            headers[etag_header.pop('name')] = etag_header

        responses: ResponseType = {}

        # We don't(!) support any endpoint without an output schema.
        # Just define one!
        if self.response_schema is not None:
            responses['200'] = {
                'content': {
                    self.content_type: {
                        'schema': self.response_schema
                    },
                },
                'description': self.status_descriptions.get(
                    200,
                    'The operation was done successfully.' if self.method != 'get' else '',
                ),
                'headers': headers,
            }

        if self.will_do_redirects:
            responses['302'] = {
                'description': self.status_descriptions.get(
                    302,
                    'Either the resource has moved or has not yet completed. Please see this '
                    'resource for further information.',
                )
            }

        # Actually, iff you don't want to give out anything, then we don't need a schema.
        if self.output_empty:
            responses['204'] = {
                'description': self.status_descriptions.get(
                    204,
                    'Operation done successfully. No further output.',
                ),
                'headers': headers,
            }

        docstring_name = _docstring_name(module_obj.__doc__)
        tag_obj: OpenAPITag = {
            'name': docstring_name,
            'x-displayName': docstring_name,
        }
        docstring_desc = _docstring_description(module_obj.__doc__)
        if docstring_desc:
            tag_obj['description'] = docstring_desc
        _add_tag(tag_obj, tag_group=self.tag_group)

        operation_spec: OperationSpecType = {
            'operationId': self.operation_id,
            'tags': [docstring_name],
            'description': '',
            'responses': {
                'default': {
                    'description': 'Any unsuccessful or unexpected result.',
                    'content': {
                        'application/problem+json': {
                            'schema': ApiError,
                        }
                    }
                }
            },
        }

        header_params: List[RawParameter] = []
        query_params: Sequence[
            RawParameter] = self.query_params if self.query_params is not None else []
        path_params: Sequence[
            RawParameter] = self.path_params if self.path_params is not None else []

        if self.etag in ('input', 'both'):
            header_params.append(ETAG_IF_MATCH_HEADER)

        operation_spec['parameters'] = coalesce_schemas([
            ('header', header_params),
            ('query', query_params),
            ('path', path_params),
        ])

        operation_spec['responses'].update(responses)

        if self.request_schema is not None:
            operation_spec['requestBody'] = {
                'required': True,
                'content': {
                    'application/json': {
                        'schema': self.request_schema,
                    }
                }
            }

        operation_spec['x-codeSamples'] = code_samples(
            self,
            header_params=header_params,
            path_params=path_params,
            query_params=query_params,
        )

        # If we don't have any parameters we remove the empty list, so the spec will not have it.
        if not operation_spec['parameters']:
            del operation_spec['parameters']

        docstring_name = _docstring_name(self.func.__doc__)
        if docstring_name:
            operation_spec['summary'] = docstring_name
        else:
            raise RuntimeError(f"Please put a docstring onto {self.operation_id}")
        docstring_desc = _docstring_description(self.func.__doc__)
        if docstring_desc:
            operation_spec['description'] = docstring_desc

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

          >>> class Params(Schema):
          ...      bar = fields.String()

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
            f"{schema_params!r}")

    if missing_in_path:
        raise ValueError(f"Params {missing_in_path!r} not used in path {path}. "
                         f"Found params: {path_params!r}")


def _assign_to_tag_group(tag_group: str, name: str) -> None:
    for group in SPEC.options.setdefault('x-tagGroups', []):
        if group['name'] == tag_group:
            group['tags'].append(name)
            break
    else:
        raise ValueError(f"x-tagGroup {tag_group} not found. Please add it to specification.py")


def _add_tag(tag: OpenAPITag, tag_group: Optional[str] = None) -> None:
    name = tag['name']
    if name in [t['name'] for t in SPEC._tags]:
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
    ref = f'#/components/schemas/{_schema_name(schema_name)}'
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
    tag: OpenAPITag = {'name': _schema_name(schema.__name__)}
    docstring_name = _docstring_name(schema.__doc__)
    if docstring_name:
        tag['x-displayName'] = docstring_name
    docstring_desc = _docstring_description(schema.__doc__)
    if docstring_desc:
        tag['description'] = docstring_desc

    tag['description'] = tag.get('description', '')
    if tag['description']:
        tag['description'] += '\n\n'
    tag['description'] += _schema_definition(schema.__name__)

    return tag


def _docstring_name(docstring: Union[Any, str, None]) -> str:
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
    parts = [part.strip() for part in apispec.utils.dedent(docstring).split("\n\n", 1)]
    if len(parts) > 0 and parts[0]:
        return parts[0]

    raise ValueError("No name for the module defined. Please add a docstring!")


def _docstring_description(docstring: Union[Any, str, None]) -> Optional[str]:
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
