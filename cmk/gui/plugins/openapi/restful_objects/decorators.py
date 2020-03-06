#!/usr/bin/env python
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
from typing import (  # pylint: disable=unused-import
    Any, Set, Dict, Optional, List, Union, Literal, Tuple,
)

import apispec  # type: ignore
import apispec.utils  # type: ignore
from connexion import problem  # type: ignore
import six
from marshmallow import Schema  # type: ignore[import]

from cmk.gui.plugins.openapi.restful_objects.response_schemas import ApiError
from cmk.gui.plugins.openapi.restful_objects.specification import (
    add_operation,
    ETAG_IF_MATCH_HEADER,
    PARAM_RE,
    SPEC,
)


def _constantly(arg):
    return lambda *args, **kw: arg


_SEEN_PATHS = set()  # type: Set[Tuple[str, str]]

ETagBehaviour = Union[Literal["input"], Literal["output"], Literal["both"]]

# Only these methods are supported.
HTTPMethod = Union[Literal["get"], Literal["post"], Literal["put"], Literal["delete"]]

Parameter = str

ResponseSchema = Optional[Schema]
RequestSchema = Optional[Schema]


def endpoint_schema(
    path,  # type: str
    method='get',  # type: HTTPMethod
    parameters=None,  # type: List[Parameter]
    output_empty=False,  # type: bool
    response_schema=None,  # type: ResponseSchema
    request_schema=None,  # type: RequestSchema
    request_body_required=True,  # type: bool
    error_schema=ApiError,  # type: Schema
    etag=None,  # type: ETagBehaviour
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

        method (str):
            The HTTP method under which the endpoint should be accessible. Methods are written
            lowercase in the OpenAPI YAML-file, though both upper and lower-cased method-names
            are supported here.

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

    path_and_method = (path, method)
    if path_and_method in _SEEN_PATHS:
        raise ValueError("%s [%s] must be unique. Already defined." % path_and_method)
    _SEEN_PATHS.add(path_and_method)

    if etag is not None and etag not in ('input', 'output', 'both'):
        raise ValueError("etag must be one of 'input', 'output', 'both'.")

    if not output_empty and response_schema is None:
        raise ValueError("'output_schema' required when output is to be sent!")

    if output_empty and response_schema:
        raise ValueError("On empty output 'output_schema' may not be used.")

    if parameters is None:
        parameters = []

    param_names = _names_of(parameters)

    for path_param in PARAM_RE.findall(path):
        if path_param not in param_names:
            raise ValueError("Param %r, which is used in the HTTP path, was not specified." %
                             (path_param,))

    for param in parameters:
        if isinstance(param, dict):
            # If a parameter gets specified twice, adding it here will throw an exception.
            # This is desired behaviour as it prevents unintentional naming clashes, which can be
            # dangerous because parameters can be specified in different locations.
            SPEC.components.parameter(param['name'], param['in'], param)

    global_param_names = SPEC.components.to_dict().get('parameters', {}).keys()
    for param in parameters:
        if isinstance(param, six.string_types) and param not in global_param_names:
            raise ValueError("Param %r, which is required, was specified nowhere." % (param,))

    # We don't(!) support any endpoint without an output schema.
    # Just define one!
    if response_schema:
        path_item = {
            '200': {
                'content': {
                    'application/json': {
                        'schema': response_schema
                    },
                },
                'description': apispec.utils.dedent(response_schema.__doc__ or ''),
            }
        }

    # Actually, iff you don't want to give out anything, then we don't need a schema.
    if output_empty:
        path_item = {'204': {'description': 'Operation done successfully. No further output.'}}

    def _add_api_spec(func):
        operation_spec = {
            'operationId': func.__module__ + "." + func.__name__,
            'responses': {
                'default': {
                    'description': 'Any unsuccessful or unexpected result.',
                    'content': {
                        'application/json': {
                            'schema': error_schema,
                        }
                    }
                }
            },
            'parameters': [],
        }

        if param_names:
            operation_spec['parameters'].extend(parameters)

        if etag in ('input', 'both'):
            operation_spec['parameters'].append(ETAG_IF_MATCH_HEADER)

        if etag in ('output', 'both'):
            # We can't put this completely in a schema because 'headers' is a map. We therefore
            # have to duplicate it every time.

            # NOTE: Be aware that this block only works under the assumption that only one(!)
            # http_status defined `operation_spec`. If this assumption no longer holds this block
            # needs to be refactored.
            path_item[path_item.keys()[0]]['headers'] = {
                'ETag': {
                    'schema': {
                        'type': 'string',
                        'pattern': '[0-9a-fA-F]{32}',
                    },
                    'description': ('The HTTP ETag header for this resource. It identifies the '
                                    'current state of the object and needs to be sent along for '
                                    'subsequent modifications.')
                }
            }

        operation_spec['responses'].update(path_item)

        if request_schema is not None:
            operation_spec['requestBody'] = {
                'required': request_body_required,
                'content': {
                    'application/json': {
                        'schema': request_schema,
                    }
                }
            }

        # If we don't have any parameters we remove the empty list, so the spec will not have it.
        if not operation_spec['parameters']:
            del operation_spec['parameters']

        operation_spec.update(_docstring_keys(func))
        apispec.utils.deepupdate(operation_spec, options)

        add_operation(path, method, operation_spec)

        if response_schema is None and request_schema is None:
            return func

        return wrap_with_validation(func, request_schema, response_schema)

    return _add_api_spec


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


def _docstring_keys(func):
    # type: (Any) -> Dict[str, str]
    if not func.__doc__:
        return {}

    parts = apispec.utils.dedent(func.__doc__).split("\n\n", 1)
    if len(parts) == 1:
        return {
            'summary': func.__doc__.strip(),
        }
    elif len(parts) == 2:
        summary, long_desc = parts
        return {
            'summary': summary.strip(),
            'description': long_desc.strip(),
        }

    return {}


def _names_of(params):
    """

    Args:
        params:

    Returns:

    Examples:

        >>> _names_of(['a', 'b', 'c'])
        ['a', 'b', 'c']

        >>> _names_of(['a', {'name': 'b'}, 'c'])
        ['a', 'b', 'c']

    """
    return [p['name'] if isinstance(p, dict) else p for p in params]
