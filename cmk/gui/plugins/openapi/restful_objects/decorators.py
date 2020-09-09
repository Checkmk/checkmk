#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Decorators to expose API endpoints.

Decorating a function with `endpoint_schema` will result in a change of the SPEC object,
which then has to be dumped into the checkmk.yaml file for use by connexion and SwaggerUI.

Response validation will be done in `endpoint_schema` itself. Response validation provided by
connexion is disabled.

"""
import dataclasses
import functools
from types import FunctionType
from typing import Any, Dict, List, Optional, Sequence, Set, Union

import apispec  # type: ignore[import]
import apispec.utils  # type: ignore[import]
from apispec.ext.marshmallow import resolve_schema_instance  # type: ignore[import]
from connexion import problem, ProblemException  # type: ignore[import]
from marshmallow import Schema  # type: ignore[import]
from werkzeug.utils import import_string

from cmk.gui.plugins.openapi.restful_objects.code_examples import code_samples
from cmk.gui.plugins.openapi.restful_objects.parameters import (
    ETAG_HEADER_PARAM,
    ETAG_IF_MATCH_HEADER,
)
from cmk.gui.plugins.openapi.restful_objects.params import path_parameters
from cmk.gui.plugins.openapi.restful_objects.response_schemas import ApiError
from cmk.gui.plugins.openapi.restful_objects.specification import find_all_parameters, SPEC
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    AnyParameterAndReference,
    ENDPOINT_REGISTRY,
    EndpointName,
    ETagBehaviour,
    HTTPMethod,
    OpenAPITag,
    OperationSpecType,
    ParamDict,
    ParameterReference,
    PrimitiveParameter,
    RequestSchema,
    ResponseSchema,
    ResponseType,
    SchemaInstanceOrClass,
    ValidatorType,
)


def _constantly(arg):
    return lambda *args, **kw: arg


_SEEN_ENDPOINTS: Set[FunctionType] = set()

# FIXME: Group of endpoints is currently derived from module-name. This prevents sub-packages.


def _reduce_to_primitives(
    parameters: Optional[Sequence[AnyParameterAndReference]],
) -> List[Union[PrimitiveParameter, ParameterReference]]:
    return [p.to_dict() if isinstance(p, ParamDict) else p for p in (parameters or [])]


@dataclasses.dataclass
class Endpoint:
    """Mark the function as a REST-API endpoint.

    Notes:
        This decorator populates a global `apispec.APISpec` instance, so in order to have every
        possible endpoint in the resulting spec-file all of the endpoints have to be imported
        before reading out the APISpec instance.

    Args:
        path:
            The URI. Can contain 0-N placeholders like this: /path/{placeholder1}/{placeholder2}.
            These variables have to be defined elsewhere first. See the `specification` module.

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

        parameters:
            A list of parameter-names which are required by this endpoint. These parameters have
            to be defined elsewhere.

        output_empty:
            When set to `True`, no output will be sent to the client and the HTTP status code
            will be set to 204 (OK, no-content). No response validation will be done.

        response_schema:
            The Schema with which to validate the HTTP response.

        request_schema:
            The Schema with which to validate the HTTP request. This will not validate HTTP
            headers though.

        request_body_required:
            If set to True (default), a `response_schema` will be required.

        error_schema:
            The Schema class with which to validate an HTTP error sent by the endpoint.

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
    path: str
    name: EndpointName
    method: HTTPMethod = 'get'
    parameters: Optional[Sequence[AnyParameterAndReference]] = None
    content_type: str = 'application/json'
    output_empty: bool = False
    response_schema: ResponseSchema = None
    request_schema: RequestSchema = None
    request_body_required: bool = True
    error_schema: Schema = ApiError
    etag: Optional[ETagBehaviour] = None
    will_do_redirects: bool = False
    options: Dict[str, str] = dataclasses.field(default_factory=dict)
    func: Optional[FunctionType] = None
    operation_id: Optional[str] = None

    def __call__(self, func):
        """This is the real decorator.
        Returns:
        A wrapped function. The wrapper does input and output validation.
        """
        wrapped = wrap_with_validation(func, self.request_schema, self.response_schema)

        self.func = func
        self.operation_id = func.__module__ + "." + func.__name__

        ENDPOINT_REGISTRY.add_endpoint(
            self,
            find_all_parameters(_reduce_to_primitives(self.parameters)),
        )

        if not self.output_empty and self.response_schema is None:
            raise ValueError(
                f"{self.operation_id}: 'response_schema' required when output will be sent!")

        if self.output_empty and self.response_schema:
            raise ValueError(
                f"{self.operation_id}: On empty output 'output_schema' may not be used.")

        return wrapped

    def to_operation_dict(self) -> OperationSpecType:
        """Generate the openapi spec part of this endpoint.

        The result needs to be added to the `apispec` instance manually.
        """
        assert self.func is not None, "This object must be used in a decorator environment."
        assert self.operation_id is not None, "This object must be used in a decorator environment."

        module_obj = import_string(self.func.__module__)
        module_name = module_obj.__name__

        headers: Dict[str, PrimitiveParameter] = {}
        if self.etag in ('output', 'both'):
            headers.update(ETAG_HEADER_PARAM.header_dict())

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
                'description': apispec.utils.dedent(self.response_schema.__doc__ or ''),
                'headers': headers,
            }

        if self.will_do_redirects:
            responses['302'] = {
                'description':
                    ('Either the resource has moved or has not yet completed. Please see this '
                     'resource for further information.')
            }

        # Actually, iff you don't want to give out anything, then we don't need a schema.
        if self.output_empty:
            responses['204'] = {
                'description': 'Operation done successfully. No further output.',
                'headers': headers,
            }

        tag_obj: OpenAPITag = {
            'name': module_name,
        }
        docstring_name = _docstring_name(module_obj.__doc__)
        if docstring_name:
            tag_obj['x-displayName'] = docstring_name
        docstring_desc = _docstring_description(module_obj.__doc__)
        if docstring_desc:
            tag_obj['description'] = docstring_desc
        _add_tag(tag_obj, tag_group='Endpoints')

        operation_spec: OperationSpecType = {
            'operationId': self.operation_id,
            'tags': [module_name],
            'description': '',
            'responses': {
                'default': {
                    'description': 'Any unsuccessful or unexpected result.',
                    'content': {
                        'application/problem+json': {
                            'schema': self.error_schema,
                        }
                    }
                }
            },
            'parameters': _reduce_to_primitives(self.parameters),
        }

        if self.etag in ('input', 'both'):
            operation_spec['parameters'].append(ETAG_IF_MATCH_HEADER.to_dict())

        operation_spec['responses'].update(responses)

        if self.request_schema is not None:
            tag = _tag_from_schema(self.request_schema)
            _add_tag(tag, tag_group='Request Schemas')

            operation_spec['requestBody'] = {
                'required': self.request_body_required,
                'content': {
                    'application/json': {
                        'schema': self.request_schema,
                    }
                }
            }

        operation_spec['x-codeSamples'] = code_samples(
            self.path,
            self.method,
            self.request_schema,
            operation_spec,
        )

        # If we don't have any parameters we remove the empty list, so the spec will not have it.
        if not operation_spec['parameters']:
            del operation_spec['parameters']

        docstring_name = _docstring_name(self.func.__doc__)
        if docstring_name:
            operation_spec['summary'] = docstring_name
        docstring_desc = _docstring_description(self.func.__doc__)
        if docstring_desc:
            operation_spec['description'] = docstring_desc

        apispec.utils.deepupdate(operation_spec, self.options)

        return operation_spec


# Compat
endpoint_schema = Endpoint


def _verify_parameters(
    path: str,
    parameters: List[Union[PrimitiveParameter, ParameterReference]],
):
    """Verifies matching of parameters to the placeholders used in an URL-Template

    This works both ways, ensuring that no parameter is supplied which is then not used and that
    each template-variable in the URL-template has a corresponding parameter supplied,
    either globally or locally.

    Args:
        path:
            The URL-Template, for eample: '/user/{username}'

        parameters:
            A list of parameters. A parameter can either be a string referencing a
            globally defined parameter by name, or a dict containing a full parameter.

    Examples:

        In case of success, this function will return nothing.

          >>> _verify_parameters('/foo/{bar}', [{'name': 'bar', 'in': 'path'}])

        Yet, when problems are found, ValueErrors are raised.

          >>> _verify_parameters('/foo', [{'name': 'foo', 'in': 'path'}])
          Traceback (most recent call last):
          ...
          ValueError: Param 'foo', which is specified as 'path', not used in path. Found params: []

          >>> _verify_parameters('/foo/{bar}', [])
          Traceback (most recent call last):
          ...
          ValueError: Param 'bar', which is used in the HTTP path, was not specified.

          >>> _verify_parameters('/foo/{foobazbar}', ['foobazbar'])
          Traceback (most recent call last):
          ...
          ValueError: Param 'foobazbar', assumed globally defined, was not found.

    Returns:
        Nothing.

    Raises:
        ValueError in case of a mismatch.

    """
    param_names = _names_of(parameters)
    path_params = path_parameters(path)
    for path_param in path_params:
        if path_param not in param_names:
            raise ValueError(
                f"Param {repr(path_param)}, which is used in the HTTP path, was not specified.")

    for param in parameters:
        if isinstance(param, dict) and param['in'] == 'path' and param['name'] not in path_params:
            raise ValueError(
                f"Param {repr(param['name'])}, which is specified as 'path', not used in path. "
                f"Found params: {path_params}")

    find_all_parameters(parameters, errors='raise')


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


def wrap_with_validation(func, request_schema: RequestSchema, response_schema: ResponseSchema):
    """Wrap a function with schema validation logic.

    Args:
        func: The function to wrap

        request_schema:
            Optionally, a request-schema which actually won't get used, as long as the `connexion`
            library still does the input-validation.

        response_schema:
            Optionally, a response-schema, which *will* get validated if passed.

    Returns:
        The wrapping function.
    """
    if response_schema is None and request_schema is None:
        return func

    validate_response: ValidatorType

    if response_schema:
        validate_response = response_schema().validate
    else:
        validate_response = _constantly(None)

    @functools.wraps(func)
    def _validating_wrapper(param):
        body = schema_loads(request_schema, param.get('body', {}))
        if body is not None:
            param['body'] = body

        # FIXME ARGH
        response = func(param)
        if not hasattr(response, 'original_data'):
            return response

        # FIXME
        # We need to get the "original data" somewhere and are currently "piggy-backing"
        # it on the response instance. This is somewhat problematic because it's not
        # expected behaviour and not a valid interface of Response. Needs refactoring.
        errors = validate_response(response.original_data)
        if errors:
            # Hope we never get here in production.
            return problem(
                status=500,
                title="Server was about to send an invalid response.",
                detail="This is an error of the implementation.",
                ext={'errors': errors},
            )
        return response

    return _validating_wrapper


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


def _tag_from_schema(schema: SchemaInstanceOrClass) -> OpenAPITag:
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

        >>> tag = _tag_from_schema(TestSchema())
        >>> assert tag == expected, tag

    Args:
        schema (marshmallow.Schema):
            A marshmallow Schema class or instance.

    Returns:
        A dict containing the tag name and the description, which is taken from

    """
    if getattr(schema, '__name__', None) is None:
        return _tag_from_schema(schema.__class__)

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


def _docstring_name(docstring: Union[Any, str, None]) -> Optional[str]:
    """Split the docstring by title and rest.

    This is part of the rest.

    >>> _docstring_name(_docstring_name.__doc__)
    'Split the docstring by title and rest.'

    Args:
        docstring:

    Returns:
        A string or nothing.

    """ ""
    if not docstring:
        return None
    parts = apispec.utils.dedent(docstring).split("\n\n", 1)
    if len(parts) > 0:
        return parts[0].strip()
    return None


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


def _names_of(params: Sequence[AnyParameterAndReference]) -> Sequence[ParameterReference]:
    """Give a list of parameter names

    Both dictionary and string form are supported. See examples.

    Args:
        params: A list of params (dict or string).

    Returns:
        A list of parameter names.

    Examples:
        >>> _names_of(['a', 'b', 'c'])
        ['a', 'b', 'c']

        >>> _names_of(['a', {'name': 'b'}, 'c'])
        ['a', 'b', 'c']

    Examples:

        >>> _names_of(['a', 'b', 'c'])
        ['a', 'b', 'c']

        >>> _names_of(['a', {'name': 'b'}, ParamDict.create('c', 'query')])
        ['a', 'b', 'c']

    """
    return [p['name'] if isinstance(p, (dict, ParamDict)) else p for p in params]


def schema_loads(schema, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate a schema and populate it with the defaults.

    Examples:

        >>> from marshmallow import Schema
        >>> from cmk.gui.plugins.openapi import fields
        >>> class Foo(Schema):
        ...      integer = fields.Integer(required=True)
        ...      hello = fields.String(enum=['World'], required=True)
        ...      default_value = fields.String(missing='was populated')

        If not all required fields are passed, a ProblemException is being raised.

            >>> schema_loads(Foo, {})
            Traceback (most recent call last):
            ...
            connexion.exceptions.ProblemException

            >>> schema_loads(Foo, {'hello': 'Bob', 'integer': 10})
            Traceback (most recent call last):
            ...
            connexion.exceptions.ProblemException

        If validation passes, missing keys are populated with default values as well.

            >>> expected = {
            ...     'default_value': 'was populated',
            ...     'hello': 'World',
            ...     'integer': 10,
            ... }
            >>> res = schema_loads(Foo, {'hello': 'World', 'integer': "10"})
            >>> assert res == expected, res

    Args:
        schema:
            A marshmallow schema class, schema instance or name of a schema.
        data:
            A dictionary with data that should be checked against the schema.

    Returns:
        A new dictionary with the values converted and the defaults populated.

    """
    if schema is None:
        return None
    schema_ = resolve_schema_instance(schema)
    result = schema_.load(data)
    if result.errors:
        raise ProblemException(
            status=400,
            title="The request could not be validated.",
            detail="There is an error in your submitted data.",
            ext={'errors': result.errors},
        )
    return result.data
