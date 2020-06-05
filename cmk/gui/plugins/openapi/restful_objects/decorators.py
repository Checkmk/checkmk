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
import functools
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union, Sequence, Literal

import apispec  # type: ignore[import]
import apispec.utils  # type: ignore[import]
from connexion import problem  # type: ignore[import]
from marshmallow import Schema  # type: ignore[import]
from werkzeug.utils import import_string

from cmk.gui.plugins.openapi.restful_objects.code_examples import code_samples
from cmk.gui.plugins.openapi.restful_objects.utils import ENDPOINT_REGISTRY, PARAM_RE, ParamDict
from cmk.gui.plugins.openapi.restful_objects.response_schemas import ApiError
from cmk.gui.plugins.openapi.restful_objects.specification import (
    add_operation,
    SPEC,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import ETAG_IF_MATCH_HEADER, \
    ETAG_HEADER_PARAM
from cmk.gui.plugins.openapi.restful_objects.type_defs import EndpointName, RestfulEndpointName


def _constantly(arg):
    return lambda *args, **kw: arg


_SEEN_PATHS = set()  # type: Set[Tuple[str, str, str]]

ETagBehaviour = Literal["input", "output", "both"]

# We only support these methods.
HTTPMethod = Literal["get", "post", "put", "delete"]
Parameter = Union[ParamDict, str]
PrimitiveParameter = Union[Dict[str, Any], str]

ResponseSchema = Optional[Schema]
RequestSchema = Optional[Schema]

# FIXME: Group of endpoints is currently derived from module-name. This prevents sub-packages.


def reduce_to_primitives(parameters):
    # type: (Optional[List[Parameter]]) -> List[PrimitiveParameter]
    return [p.to_dict() if isinstance(p, ParamDict) else p for p in (parameters or [])]


def endpoint_schema(
        path,  # type: str
        name,  # type: Union[EndpointName, RestfulEndpointName]
        method='get',  # type: HTTPMethod
        parameters=None,  # type: List[Parameter]
        content_type='application/json',  # type: str
        output_empty=False,  # type: bool
        response_schema=None,  # type: ResponseSchema
        request_schema=None,  # type: RequestSchema
        request_body_required=True,  # type: bool
        error_schema=ApiError,  # type: Schema
        etag=None,  # type: ETagBehaviour
        will_do_redirects=False,  # type: bool
        **options  # type: dict
):
    """Mark the function as a REST-API endpoint.

    Notes:
        This decorator populates a global `apispec.APISpec` instance, so in order to have every
        possible endpoint in the resulting spec-file all of the endpoints have to be imported
        before reading out the APISpec instance.

    Args:
        path (str):
            The URI. Can contain 0-N placeholders like this: /path/{placeholder1}/{placeholder2}.
            These variables have to be defined elsewhere first. See the `specification` module.

        name (EndpointName):
            The name of the endpoint. This is the name where this endpoint is "registered" under
            and can only be used once globally.

        method (str):
            The HTTP method under which the endpoint should be accessible. Methods are written
            lowercase in the OpenAPI YAML-file, though both upper and lower-cased method-names
            are supported here.

        content_type (str):
            The content-type under which this endpoint shall be executed. Multiple endpoints may
            be defined for any one URL, but only one endpoint per url-content-type combination.

        parameters (list):
            A list of parameter-names which are required by this endpoint. These parameters have
            to be defined elsewhere.

        output_empty (bool):
            When set to `True`, no output will be sent to the client and the HTTP status code
            will be set to 204 (OK, no-content). No response validation will be done.

        response_schema (marshmallow.Schema):
            The Schema with which to validate the HTTP response.

        request_schema (marshmallow.Schema):
            The Schema with which to validate the HTTP request. This will not validate HTTP
            headers though.

        request_body_required (bool):
            If set to True (default), a `response_schema` will be required.

        error_schema (marshmallow.Schema):
            The Schema class with which to validate an HTTP error sent by the endpoint.

        etag (str):
            One of 'input', 'output', 'both'. When set to 'input' a valid ETag is required in
            the 'If-Match' request header. When set to 'output' a ETag is sent to the client
            with the 'ETag' response header. When set to 'both', it will act as if set to
            'input' and 'output' at the same time.

        will_do_redirects (bool):
            This endpoint can also emit a 302 response (moved temporarily) code. Setting this to
            true will add this to the specification and documentation. Defaults to False.

        **options (dict):
            Various keys which will be directly applied to the OpenAPI operation object.

    Returns:
        A wrapped function or the function unmodified. This depends on the need for validation.
        When no validation is needed, no wrapper is applied.

    """
    # NOTE:
    #
    # The implementation of this decorator may seem a bit daunting at first, but it is actually
    # quite straight-forward.
    #
    # Everything outside the `_add_api_spec` function is not dependent on the endpoint specifics
    # though it may depend on other parameters. (e.g. schemas etc)
    #
    # Everything inside of it needs the decorated function for filling out the spec.
    #

    endpoint_identifier = (path, method, content_type)
    if endpoint_identifier in _SEEN_PATHS:
        raise ValueError("%s [%s, %s] must be unique. Already defined." % endpoint_identifier)
    _SEEN_PATHS.add(endpoint_identifier)

    if etag is not None and etag not in ('input', 'output', 'both'):
        raise ValueError("etag must be one of 'input', 'output', 'both'.")

    primitive_parameters = reduce_to_primitives(parameters)
    del parameters
    param_names = _names_of(primitive_parameters)

    for path_param in PARAM_RE.findall(path):
        if path_param not in param_names:
            raise ValueError("Param %r, which is used in the HTTP path, was not specified." %
                             (path_param,))

    global_param_names = SPEC.components.to_dict().get('parameters', {}).keys()
    for param in primitive_parameters:
        if isinstance(param, str) and param not in global_param_names:
            raise ValueError("Param %r, which is required, was specified nowhere." % (param,))

    def _add_api_spec(func):
        module_obj = import_string(func.__module__)
        module_name = module_obj.__name__
        operation_id = func.__module__ + "." + func.__name__
        endpoint_key = (module_name, name)

        try:
            ENDPOINT_REGISTRY[endpoint_key] = {
                'path': path,
                'method': method,
                'parameters': primitive_parameters,
            }
        except ValueError:
            raise RuntimeError("The endpoint %r has already been set to %r" %
                               (endpoint_key, ENDPOINT_REGISTRY[endpoint_key]))

        if not output_empty and response_schema is None:
            raise ValueError("%s: 'response_schema' required when output is to be sent!" %
                             operation_id)

        if output_empty and response_schema:
            raise ValueError("%s: On empty output 'output_schema' may not be used." % operation_id)

        path_item = {}
        # We don't(!) support any endpoint without an output schema.
        # Just define one!
        if response_schema is not None:
            path_item['200'] = {
                'content': {
                    content_type: {
                        'schema': response_schema
                    },
                },
                'description': apispec.utils.dedent(response_schema.__doc__ or ''),
            }

        if will_do_redirects:
            path_item['302'] = {
                'description':
                    ('Either the resource has moved or has not yet completed. Please see this '
                     'resource for further information.')
            }

        # Actually, iff you don't want to give out anything, then we don't need a schema.
        if output_empty:
            path_item['204'] = {'description': 'Operation done successfully. No further output.'}

        tag_obj = {'name': module_name}
        tag_obj.update(_docstring_keys(module_obj.__doc__, 'x-displayName', 'description'))
        _add_tag(tag_obj, tag_group='Endpoints')

        operation_spec = {
            'operationId': operation_id,
            'tags': [module_name],
            'description': '',
            'responses': {
                'default': {
                    'description': 'Any unsuccessful or unexpected result.',
                    'content': {
                        'application/problem+json': {
                            'schema': error_schema,
                        }
                    }
                }
            },
            'parameters': primitive_parameters,
        }

        if etag in ('input', 'both'):
            operation_spec['parameters'].append(ETAG_IF_MATCH_HEADER.to_dict())

        if etag in ('output', 'both'):
            # We can't put this completely in a schema because 'headers' is a map. We therefore
            # have to duplicate it every time.

            # NOTE: Be aware that this block only works under the assumption that only one(!)
            # http_status defined `operation_spec`. If this assumption no longer holds this block
            # needs to be refactored.
            only_key = list(path_item.keys())[0]
            path_item[only_key].setdefault('headers', {})
            path_item[only_key]['headers'].update(ETAG_HEADER_PARAM.header_dict())

        operation_spec['responses'].update(path_item)

        if request_schema is not None:
            tag = _tag_from_schema(request_schema)
            _add_tag(tag, tag_group='Request Schemas')

            operation_spec['requestBody'] = {
                'required': request_body_required,
                'content': {
                    'application/json': {
                        'schema': request_schema,
                    }
                }
            }

        operation_spec['x-codeSamples'] = code_samples(path, method, request_schema, operation_spec)

        # If we don't have any parameters we remove the empty list, so the spec will not have it.
        if not operation_spec['parameters']:
            del operation_spec['parameters']

        operation_spec.update(_docstring_keys(func.__doc__, 'summary', 'description'))
        apispec.utils.deepupdate(operation_spec, options)

        add_operation(path, method, operation_spec)

        if response_schema is None and request_schema is None:
            return func

        return wrap_with_validation(func, request_schema, response_schema)

    return _add_api_spec


def _assign_to_tag_group(tag_group, name):
    # type: (str, str) -> None
    for group in SPEC.options.setdefault('x-tagGroups', []):
        if group['name'] == tag_group:
            group['tags'].append(name)
            break
    else:
        raise ValueError("x-tagGroup %s not found. Please add it to specification.py" %
                         (tag_group,))


def _add_tag(tag, tag_group=None):
    # type: (dict, Optional[str]) -> None
    name = tag['name']
    if name in [t['name'] for t in SPEC._tags]:
        return

    SPEC.tag(tag)
    if tag_group is not None:
        _assign_to_tag_group(tag_group, name)


def wrap_with_validation(func, _request_schema, response_schema):
    """Wrap a function """
    if response_schema:
        validate_response = response_schema().validate
    else:
        validate_response = _constantly(None)

    @functools.wraps(func)
    def _validating_wrapper(*args, **kw):
        # noinspection PyArgumentList
        response = func(*args, **kw)
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
                title=u"Server was about to send an invalid response.",
                detail=u"This is an error of the implementation.",
                ext={'errors': errors},
            )
        return response

    return _validating_wrapper


def _schema_name(schema):
    return schema.__name__.rstrip("Schema")


def _schema_definition(schema):
    ref = '#/components/schemas/%s' % (_schema_name(schema),)
    definition = '<SchemaDefinition schemaRef="%s" showReadOnly={true} showWriteOnly={true} />' % (
        ref,)
    return definition


def _tag_from_schema(schema):
    # type: (Union[Schema, Type[Schema]]) -> dict
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

    tag = {'name': _schema_name(schema)}
    tag.update(_docstring_keys(schema.__doc__, 'x-displayName', 'description'))

    tag['description'] = tag.get('description', '')
    if tag['description']:
        tag['description'] += '\n\n'
    tag['description'] += _schema_definition(schema)

    return tag


def _docstring_keys(docstring, title, description):
    # type: (Union[Any, str, None], str, str) -> Dict[str, str]
    """Split the docstring by title and rest.

    This is part of the rest.

    Examples:
        >>> _docstring_keys(_docstring_keys.__doc__, 'summary', 'desc')['summary']
        'Split the docstring by title and rest.'

    Args:
        docstring:
        title:
        description:

    Returns:

    """
    if not docstring:
        return {}

    parts = apispec.utils.dedent(docstring).split("\n\n", 1)
    if len(parts) == 1:
        return {
            title: docstring.strip(),
        }
    if len(parts) == 2:
        summary, long_desc = parts
        return {
            title: summary.strip(),
            description: long_desc.strip(),
        }

    return {}


def _names_of(params):
    # type: (List[PrimitiveParameter]) -> Sequence[PrimitiveParameter]
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

        >>> _names_of(['a', {'name': 'b'}, 'c'])
        ['a', 'b', 'c']

    """
    return [p['name'] if isinstance(p, dict) else p for p in params]
