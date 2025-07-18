#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections import abc
from collections.abc import ItemsView, Mapping, Sequence

from marshmallow import Schema

from cmk import fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.type_defs import (
    LocationType,
    OpenAPIParameter,
    RawParameter,
    translate_to_openapi_keys,
)
from cmk.utils.datastructures import denilled

PARAM_RE = re.compile(r"{([a-z][a-z0-9_]*)}")


def path_parameters(path: str) -> list[str]:
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


def marshmallow_to_openapi(
    params: RawParameter | Sequence[RawParameter] | None,
    location: LocationType,
) -> Sequence[OpenAPIParameter]:
    """Put the 'in' key into a all parameters in a list.

    Examples:

        >>> class Params(Schema):
        ...      field1 = fields.String(required=True, allow_none=True)
        ...      field2 = fields.String(example="foo", required=False)

        >>> marshmallow_to_openapi([Params], 'query')
        [{'name': 'field1', 'in': 'query', 'required': True, 'allowEmptyValue': True, \
'schema': {'type': 'string'}}, \
{'name': 'field2', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'example': 'foo', 'schema': {'type': 'string'}}]

        >>> marshmallow_to_openapi([{'field1': fields.String()}], 'query')
        [{'name': 'field1', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'schema': {'type': 'string'}}]

        >>> marshmallow_to_openapi([{'field2': fields.String()}], 'query')
        [{'name': 'field2', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'schema': {'type': 'string'}}]

        >>> marshmallow_to_openapi([{'field1': fields.String(), 'field2': fields.String()}], 'query')
        [{'name': 'field1', 'in': 'query', 'required': False, 'allowEmptyValue': False, \
'schema': {'type': 'string'}}, \
{'name': 'field2', 'in': 'query', 'required': False, 'allowEmptyValue': False, 'schema': \
{'type': 'string'}}]

        >>> marshmallow_to_openapi([Schema], 'query')
        []

        >>> marshmallow_to_openapi([{}], 'query')
        []

        >>> marshmallow_to_openapi(None, 'query')
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

    def _is_field_param(dict_: dict) -> bool:
        return all(isinstance(value, fields.Field) for value in dict_.values())

    def _is_schema_class(klass: RawParameter) -> bool:
        return isinstance(klass, type) and issubclass(klass, Schema)

    result: list[OpenAPIParameter] = []
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
            metadata = denilled(
                {
                    "description": field.metadata.get("description"),
                    "example": field.metadata.get("example"),
                    "required": (
                        field.required or location == "path"
                    ),  # path parameters are always required
                    "allow_empty": (
                        field.allow_none if location == "query" else None
                    ),  # only allowed for query parameters
                    "schema_enum": field.metadata.get("enum"),
                    "schema_string_format": field.metadata.get("format"),
                    "schema_string_pattern": field.metadata.get("pattern"),
                    "schema_num_minimum": field.metadata.get("minimum"),
                    "schema_num_maximum": field.metadata.get("maximum"),
                }
            )
            result.append(translate_to_openapi_keys(name=name, location=location, **metadata))
    return result


def to_schema(params: Sequence[RawParameter] | RawParameter | None) -> type[Schema] | None:
    """
    Examples:

        >>> to_schema(None)

        >>> to_schema([])

        >>> class Foo(Schema):
        ...       field = fields.String(description="Foo")

        >>> dict(to_schema([Foo])().declared_fields)  # doctest: +ELLIPSIS
        {'field': <fields.String(...)>}

        >>> to_schema({
        ...     'foo': fields.String(description="Foo")
        ... })().declared_fields['foo'] # doctest: +ELLIPSIS
        <fields.String(...)>

        >>> to_schema(marshmallow_to_openapi([{'name': fields.String(description="Foo")}], 'path'))
        <class 'abc.GeneratedSchema'>

        >>> s = to_schema(
        ...     [
        ...         {'name': fields.String(description="Foo")},
        ...         {'title': fields.String(description="Foo")},
        ...     ],
        ... )
        >>> s
        <class 'abc.GeneratedSchema'>

        All fields of all dicts are put into one Schema

        >>> assert isinstance(s().declared_fields['name'], fields.String)
        >>> assert isinstance(s().declared_fields['title'], fields.String)

    Args:
        params:
            The following types are supported:
                * dicts with a "name" to "fields.Field" mapping.
                * marshmallow schemas

            Additonally a heterogenous sequence of one or more of those types is also supported

    Returns:
        A marshmallow schema with all the fields unified

    """

    def _validate_fields(name, dict_):
        for key, field in dict_.items():
            if "description" not in field.metadata:
                # FIXME: Add descriptions to all BI fields and schemas
                if not name.startswith("BI"):
                    raise ValueError(
                        f"{name}: field {key} has no description."
                        f"\n\n{field.metadata!r}"
                        f"\n\n{dict_!r}"
                    )

    def _from_dict(dict_):
        needs_validating = False
        for value in dict_.values():
            if isinstance(value, fields.Field):
                needs_validating = True

        if needs_validating:
            _validate_fields("dict", dict_)
        schema_class = BaseSchema.from_dict(dict_)
        assert issubclass(schema_class, BaseSchema)
        return schema_class

    if not params:
        return None

    if isinstance(params, abc.Sequence):
        p: dict[str, fields.Field] = {}
        for entry in params:
            if isinstance(entry, abc.Mapping):
                p.update(entry)
            else:
                p.update(entry().declared_fields)
        return _from_dict(p)

    if isinstance(params, abc.Mapping):
        return _from_dict(params)

    schema = params()
    _validate_fields(schema.__class__.__name__, schema.declared_fields)
    return params


def fill_out_path_template(
    orig_path: str,
    parameters: Mapping[str, OpenAPIParameter],
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
    for path_param in PARAM_RE.findall(path):  # type: str
        if path_param not in parameters:
            raise ValueError(f"Parameter {path_param!r} needed, but not supplied in {parameters!r}")

        param_spec = parameters[path_param]
        example = param_spec.get("example")
        if example is None:
            raise ValueError(f"Parameter {path_param!r} of path {orig_path!r} has no example.")
        if not isinstance(example, str):
            raise TypeError(
                f"Parameter {path_param!r} of path {orig_path!r} has an invalid example."
            )

        path = path.replace("{" + path_param + "}", example)
    return path
