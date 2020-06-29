#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import Optional, Union, Dict, Any, List, Literal

from cmk.gui.plugins.openapi.restful_objects.type_defs import LocationType, HTTPMethod
from cmk.gui.type_defs import SetOnceDict

# This is the central store for all our endpoints. We use this to determine the correct URLs at
# runtime so that we can't have typos when interlinking responses.
ENDPOINT_REGISTRY = SetOnceDict()

PARAM_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def _denilled(dict_):
    """Remove all None values from a dict.

    Examples:

        >>> _denilled({'a': None, 'foo': 'bar', 'b': None})
        {'foo': 'bar'}

    Args:
        dict_:

    Returns:
        A dict without values being None.
    """
    return {key: value for key, value in dict_.items() if value is not None}


OpenAPISchemaType = Literal['string', 'array', 'object', 'boolean', 'integer', 'number']


def _translate_to_openapi_keys(
    name: str = None,
    location: LocationType = None,
    description: Optional[str] = None,
    required: bool = None,
    example: str = None,
    allow_emtpy: bool = None,
    schema_type: OpenAPISchemaType = None,
    schema_string_pattern: Optional[str] = None,
    schema_string_format: str = None,
    schema_num_minimum: Optional[int] = None,
    schema_num_maximum: Optional[int] = None,
):
    schema: Dict[str, Any] = {'type': schema_type}
    if schema_type == 'string':
        schema.update(
            format=schema_string_format,
            pattern=schema_string_pattern,
        )
    if schema_type in ('number', 'integer'):
        schema.update(
            minimum=schema_num_minimum,
            maximum=schema_num_maximum,
        )
    raw_values = {
        'name': name,
        'in': location,
        'required': required,
        'description': description,
        'allowEmptyValue': allow_emtpy,
        'example': example,
        'schema': _denilled(schema) or None,
    }
    return raw_values


class ParamDict(dict):
    """Represents a parameter but can be changed by calling it.

    This is basically a dict, but one can return a new dict with updated parameters easily
    without having to change the original.

    Examples:

        >>> p = ParamDict(schema={'pattern': '123'})
        >>> type(p['schema'])
        <class 'dict'>

        >>> p = ParamDict(name='foo', location='query', required=True)
        >>> p
        {'name': 'foo', 'required': True, 'in': 'query'}

        >>> p(required=False)
        {'name': 'foo', 'required': False, 'in': 'query'}

        >>> p.spec_tuple()
        ('foo', 'query', {'required': True})

    """
    def __init__(self, *seq, **kwargs):
        if 'location' in kwargs:
            kwargs['in'] = kwargs.pop('location')
        for d in seq:
            if 'location' in kwargs:
                d['in'] = d.pop('location')
        super(ParamDict, self).__init__(*seq, **kwargs)

    def __call__(
        self,
        name: str = None,
        description: str = None,
        location: LocationType = None,
        required: bool = None,
        allow_empty: bool = None,
        example: str = None,
        schema_type: OpenAPISchemaType = None,
        schema_string_pattern: str = None,
        schema_string_format: str = None,
        schema_num_minimum: Optional[int] = None,
        schema_num_maximum: Optional[int] = None,
    ):
        """

        Examples:

            >>> p = ParamDict.create('foo', 'query', required=False)
            >>> p = p(
            ...     name='bar',
            ...     allow_empty=True,
            ... )
            >>> expected = {
            ...     'name': 'bar',
            ...     'in': 'query',
            ...     'required': False,
            ...     'allowEmptyValue': True,
            ...     'schema': {'type': 'string'},
            ... }
            >>> assert p == expected, p

        """
        # NOTE: The defaults are all None here, so that only the updated keys will overwrite the
        # previous values.
        new_dict = self.__class__(**self)
        raw_values = _translate_to_openapi_keys(
            name=name,
            location=location,
            description=description,
            example=example,
            required=required,
            allow_emtpy=allow_empty,
            schema_type=schema_type,
            schema_num_maximum=schema_num_maximum,
            schema_num_minimum=schema_num_minimum,
            schema_string_format=schema_string_format,
            schema_string_pattern=schema_string_pattern,
        )
        new_dict.update(_denilled(raw_values))
        return new_dict

    def __str__(self):
        """Return just the name of the parameter.

        This is useful for parameter re-use."""
        return self['name']

    @classmethod
    def create(
        cls,
        param_name: str,
        location: LocationType,
        description: Optional[str] = None,
        required: bool = True,
        allow_emtpy: bool = False,
        example: str = None,
        schema_type: OpenAPISchemaType = 'string',
        schema_string_pattern: Optional[str] = None,
        schema_string_format: str = None,
        schema_num_minimum: Optional[int] = None,
        schema_num_maximum: Optional[int] = None,
    ) -> 'ParamDict':
        """Specify an OpenAPI parameter to be used on a particular endpoint.

        Args:
            param_name:
                The name of the parameter.

            description:
                Optionally the description of the parameter. Markdown may be used.

            location:
                One of 'query', 'path', 'cookie', 'header'.

            required:
                If `location` is `path` this needs to be set and True. Otherwise it can even be absent.

            allow_emtpy:
                If None as a value is allowed.

            example:
                Example value for the documentation.

            schema_type:
                May be 'string', 'bool', etc.

            schema_string_pattern:
                A regex which is used to filter invalid values. Only  valid for `schema_type`
                being set to 'string'.

            schema_string_format:
                The format of the string.

            schema_num_minimum:
                Valid for `integer`, `number`. The minimum number.

            schema_num_maximum:
                Valid for `integer`, `number`. The maximum number.

        Examples:

            >>> p = ParamDict.create('foo', 'query', required=False)
            >>> expected = {
            ...     'name': 'foo',
            ...     'in': 'query',
            ...     'required': False,
            ...     'allowEmptyValue': False,
            ...     'schema': {'type': 'string'},
            ... }
            >>> assert p == expected, p

        Returns:
            The parameter dict.

        """
        if location == 'path' and not required:
            raise ValueError("path parameters' `required` field always needs to be True!")

        raw_values = _translate_to_openapi_keys(
            param_name,
            location,
            description=description,
            required=required,
            allow_emtpy=allow_emtpy,
            schema_type=schema_type,
            example=example,
            schema_num_maximum=schema_num_maximum,
            schema_num_minimum=schema_num_minimum,
            schema_string_format=schema_string_format,
            schema_string_pattern=schema_string_pattern,
        )
        # We throw away None valued keys so they won't show up in the specification.
        return cls(_denilled(raw_values))

    def to_dict(self):
        return dict(self)

    def spec_tuple(self):
        """Return a tuple suitable for passing into components.parameters()"""
        new = self()
        return new.pop('name'), new.pop('in'), new.to_dict()

    def header_dict(self):
        new = self()
        location = new.pop('in')
        if location != 'header':
            raise ValueError("Only header parameters can be added to the header-struct.")
        return {new.pop('name'): new.to_dict()}


param = ParamDict.create


def fill_out_path_template(orig_path, parameters):
    """Fill out a simple template.

    Examples:

        >>> param_spec = {'var': {'example': 'foo'}}
        >>> fill_out_path_template('/path/{var}', param_spec)
        '/path/foo'

        >>> param_spec = {'var_id': {'example': 'foo'}}
        >>> fill_out_path_template('/path/{var_id}', param_spec)
        '/path/foo'

    Args:
        orig_path:
        parameters:

    Returns:

    """
    path = orig_path
    for path_param in PARAM_RE.findall(path):
        param_spec = parameters[path_param]
        try:
            path = path.replace("{" + path_param + "}", param_spec['example'])
        except KeyError:
            raise KeyError("Param %s of path %r has no example" % (path_param, orig_path))
    return path


Parameter = Union[ParamDict, str]
PrimitiveParameter = Union[Dict[str, Any], str]
AnyParameter = Union[ParamDict, Dict[str, Any], str]


def make_endpoint_entry(method: HTTPMethod, path, parameters: List[AnyParameter]):
    """Create an entry necessary for the ENDPOINT_REGISTRY

    Args:
        method:
            The HTTP method of the endpoint.
        path:
            The Path template the endpoint uses.
        parameters:
            The parameters as a list of dicts or strings.

    Returns:
        A dict.

    """
    # TODO: Subclass Endpoint-Registry to have this as a method?
    return {
        'path': path,
        'method': method,
        'parameters': parameters,
    }
