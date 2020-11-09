#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Dict, ItemsView, List, Optional, Sequence, Type, Union

from marshmallow import fields, Schema
from marshmallow.schema import SchemaMeta

from cmk.gui.plugins.openapi.restful_objects.datastructures import denilled
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    LocationType,
    OpenAPIParameter,
    RawParameter,
    translate_to_openapi_keys,
)
from cmk.gui.plugins.openapi.utils import BaseSchema

PARAM_RE = re.compile(r"{([a-z][a-z0-9_]*)}")


def path_parameters(path: str) -> List[str]:
    """Give all variables from a path-template.

    Examples:

        >>> path_parameters("/objects/{domain_type}/{primary_key}")
        ['domain_type', 'primary_key']

    Args:
        path:
            The path-template.

    Returns:
        A list of variable-names.

    """
    return PARAM_RE.findall(path)


def to_openapi(
    params: Optional[Union[RawParameter, Sequence[RawParameter]]],
    location: LocationType,
) -> Sequence[OpenAPIParameter]:
    """Put the 'in' key into a all parameters in a list.

    Examples:

        >>> class Params(Schema):
        ...      field1 = fields.String(required=True, allow_none=True)
        ...      field2 = fields.String(example="foo", required=False)

        >>> to_openapi([Params], 'query')
        [{'name': 'field1', 'in': 'query', 'required': True, 'allowEmptyValue': True, \
'schema': {'type': 'string'}}, \
{'name': 'field2', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'example': 'foo', 'schema': {'type': 'string'}}]

        >>> to_openapi([{'field1': fields.String()}], 'query')
        [{'name': 'field1', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'schema': {'type': 'string'}}]

        >>> to_openapi([{'field2': fields.String()}], 'query')
        [{'name': 'field2', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'schema': {'type': 'string'}}]

        >>> to_openapi([{'field1': fields.String(), 'field2': fields.String()}], 'query')
        [{'name': 'field1', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'schema': {'type': 'string'}}, \
{'name': 'field2', 'in': 'query', 'required': False, 'allowEmptyValue': False, 'schema': \
{'type': 'string'}}]

        >>> to_openapi([Schema], 'query')
        []

        >>> to_openapi([{}], 'query')
        []

        >>> to_openapi(None, 'query')
        []

    Args:
        params:
            The list of parameters.

        location:
            The location of the parameters. May be either 'query', 'path', 'header' or 'cookie'.

    Returns:
        The list in a normalized form and the location added.

    """
    if params is None:
        return []

    if not isinstance(params, list):
        raise ValueError("Needs to be a sequence of parameters.")

    def _is_field_param(dict_):
        return all([isinstance(value, fields.Field) for value in dict_.values()])

    def _is_schema_class(klass):
        try:
            return issubclass(klass, Schema)
        except TypeError:
            return False

    result: List[OpenAPIParameter] = []
    _fields: ItemsView[str, fields.Field]
    for raw_param in params:
        if _is_schema_class(raw_param):
            raw_param = raw_param()

        if isinstance(raw_param, Schema):
            _fields = raw_param.declared_fields.items()
        elif _is_field_param(raw_param):
            _fields = raw_param.items()
        else:
            raise ValueError(f"Don't recognize parameter of form: {raw_param!r}")

        for name, field in _fields:
            metadata = denilled({
                'description': field.metadata.get('description'),
                'example': field.metadata.get('example'),
                'required': field.required,
                'allow_empty': field.allow_none,
                'schema_enum': field.metadata.get('enum'),
                'schema_string_format': field.metadata.get('format'),
                'schema_string_pattern': field.metadata.get('pattern'),
                'schema_num_minimum': field.metadata.get('minimum'),
                'schema_num_maximum': field.metadata.get('maximum'),
            })
            param = translate_to_openapi_keys(
                name=name,
                location=location,
                **metadata,
            )
            result.append(param)
    return result


def to_schema(
    params: Optional[Sequence[RawParameter]],
    required='none',
) -> Optional[Union[Type[Schema], type]]:
    """
    Examples:

        >>> to_schema(None)

        >>> to_schema([])

        >>> class Foo(Schema):
        ...       field = fields.String()

        >>> dict(to_schema([Foo])().declared_fields)  # doctest: +ELLIPSIS
        {'field': <fields.String(...)>}

        >>> to_schema(to_openapi([{'name': fields.String()}], 'path'))
        <class 'marshmallow.schema.GeneratedSchema'>

        >>> s = to_schema(
        ...     [
        ...         {'name': fields.String()},
        ...         {'title': fields.String()},
        ...     ],
        ...     'path',
        ... )
        >>> s
        <class 'marshmallow.schema.GeneratedSchema'>

        All fields of all dicts are put into one Schema

        >>> assert isinstance(s().declared_fields['name'], fields.String)
        >>> assert isinstance(s().declared_fields['title'], fields.String)

    Args:
        params:

    Returns:

    """
    if not params:
        return None

    if isinstance(params, SchemaMeta):
        return params

    def _from_dict(dict_):
        return BaseSchema.from_dict(dict_)

    if isinstance(params, list):
        p = {}
        for entry in params:
            if isinstance(entry, SchemaMeta):
                p.update(entry().declared_fields)
            else:
                p.update(entry)
        return _from_dict(p)

    # Marshmallow's type is invariant (Dict instead of Mapping) so we have to cast.
    return _from_dict(params)


def fill_out_path_template(
    orig_path: str,
    parameters: Dict[str, OpenAPIParameter],
) -> str:
    """Fill out a simple template.

    Examples:

        >>> _param_spec = {'var': {'example': 'foo'}}
        >>> fill_out_path_template('/path/{var}', _param_spec)
        '/path/foo'

        >>> _param_spec = {'var_id': {'example': 'foo'}}
        >>> fill_out_path_template('/path/{var_id}', _param_spec)
        '/path/foo'

    Args:
        orig_path:
        parameters:

    Returns:

    """
    path = orig_path
    for path_param in PARAM_RE.findall(path):
        if path_param not in parameters:
            raise ValueError(f"Parameter {path_param!r} needed, but not supplied in {parameters!r}")

        param_spec = parameters[path_param]
        if 'example' not in param_spec:
            raise ValueError(f"Parameter {path_param!r} of path {orig_path!r} has no example.")

        path = path.replace("{" + path_param + "}", param_spec['example'])
    return path
