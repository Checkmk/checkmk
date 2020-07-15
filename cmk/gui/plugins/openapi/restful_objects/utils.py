#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import Optional, Tuple, TypedDict, Union, Dict, Any, List, Literal

from cmk.gui.plugins.openapi.restful_objects.type_defs import EndpointName, LocationType, HTTPMethod


def _path_parameters(path: str) -> List[str]:
    """
    Examples:

        >>> _path_parameters("/objects/{domain_type}/{primary_key}")
        ['domain_type', 'primary_key']

    Args:
        path:

    Returns:

    """
    return PARAM_RE.findall(path)


PARAM_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def _denilled(dict_: Dict[str, Optional[Any]]) -> Dict[str, Any]:
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


def fill_out_path_template(orig_path: str, parameters: Dict[str, Dict[str, str]]):
    """Fill out a simple template.

    Examples:

        >>> _param_spec = {'var': {'example': 'foo'}}
        >>> fill_out_path_template('/path/{var}', _param_spec)
        '/path/foo'

        >>> _param_spec = {'var_id': {'example': 'foo'}}
        >>> fill_out_path_template('/path/{var_id}', _param_spec)
        '/path/foo'

        >>> _param_spec = {}
        >>> fill_out_path_template('/path/{var_id}', _param_spec)
        Traceback (most recent call last):
        ...
        ValueError: Parameter 'var_id' needed, but not supplied.

        >>> _param_spec = {'var_id': {}}
        >>> fill_out_path_template('/path/{var_id}', _param_spec)
        Traceback (most recent call last):
        ...
        ValueError: Parameter 'var_id' of path '/path/{var_id}' has no example.

    Args:
        orig_path:
        parameters:

    Returns:

    """
    path = orig_path
    for path_param in PARAM_RE.findall(path):
        if path_param not in parameters:
            raise ValueError(f"Parameter {path_param!r} needed, but not supplied.")

        param_spec = parameters[path_param]
        if 'example' not in param_spec:
            raise ValueError(f"Parameter {path_param!r} of path {orig_path!r} has no example.")

        path = path.replace("{" + path_param + "}", param_spec['example'])
    return path


Parameter = Union[ParamDict, str]
PrimitiveParameter = Union[Dict[str, Any], str]
AnyParameter = Union[ParamDict, Dict[str, Any], str]

EndpointEntry = TypedDict(
    "EndpointEntry",
    {
        'href': str,
        'method': HTTPMethod,
        'rel': EndpointName,
        'parameters': List[PrimitiveParameter],
    },
    total=True,
)

EndpointKey = Tuple[str, EndpointName]
ParameterKey = Tuple[str, ...]


# This is the central store for all our endpoints. We use this to determine the correct URLs at
# runtime so that we can't have typos when interlinking responses.
class EndpointRegistry:
    """Registry for endpoints.

    Examples:

        >>> reg = EndpointRegistry()
        >>> reg.add_endpoint("foo", ".../update", "get", "/foo/d41d8cd98f/{hostname}",
        ...                  [{'name': "hostname", 'in': 'path'}])

        >>> reg.lookup("foo", ".../update", {'hostname': 'example.com'})
        {'href': '/foo/d41d8cd98f/example.com', 'method': 'get', 'rel': '.../update', \
'parameters': [{'name': 'hostname', 'in': 'path'}]}

        >>> reg.lookup("foo", ".../update", {})
        Traceback (most recent call last):
        ...
        ValueError: Endpoint ('foo', '.../update') with parameters () not found. \
The following parameter combinations are possible: [('hostname',)]

        >>> reg = EndpointRegistry()
        >>> reg.add_endpoint("foo", ".../update", "get", "/foo",
        ...     [{'name': 'hostname', 'in': 'query', 'required': True}])

    """
    def __init__(self):
        self._endpoints: Dict[EndpointKey, Dict[ParameterKey, EndpointEntry]] = {}

    def lookup(
        self,
        module_name: str,
        rel: EndpointName,
        parameter_values: Dict[str, str],
    ) -> EndpointEntry:
        """Look up an endpoint definition

        Args:
            module_name:
                The name of the module where the endpoint has been defined in.
            rel:
                The rel of the endpoint.
            parameter_values:
                A simple mapping of parameter-names to values.

        Returns:
            An endpoint-struct.

        """
        # Wen don't need to validate the matching of parameters after this as this expects all
        # parameters to be available to be supplied, else we never get the "endpoint_key".
        endpoint_key = (module_name, rel)
        parameter_key: ParameterKey = tuple(sorted(parameter_values.keys()))
        endpoint_entry = self._endpoints[(module_name, rel)]
        if parameter_key not in endpoint_entry:
            raise ValueError(f"Endpoint {endpoint_key} with parameters {parameter_key} not found. "
                             f"The following parameter combinations are possible: "
                             f"{list(endpoint_entry.keys())}")

        endpoint = endpoint_entry[parameter_key]
        return {
            'href': _make_url(endpoint['href'], endpoint['parameters'], parameter_values),
            'method': endpoint['method'],
            'rel': rel,
            'parameters': endpoint['parameters'],
        }

    def add_endpoint(
        self,
        module_name: str,
        rel: EndpointName,
        method: HTTPMethod,
        path: str,
        parameters: List[AnyParameter],
    ) -> None:
        """Adds an endpoint to the registry

        Args:
            module_name:
                The module in which the endpoint has been defined.
            rel:
                The rel of the endpoint.
            method:
                The HTTP method of the endpoint.
            path:
                The Path template the endpoint uses.
            parameters:
                The parameters as a list of dicts or strings.

        """
        def _param_key(_path, _parameters):
            # We key on _all_ required parameters, regardless their type.
            _param_names = set()
            for _param in _parameters:
                if isinstance(_param, dict) and _param.get('required', True):
                    _param_names.add(_param['name'])
            for _param_name in _path_parameters(_path):
                _param_names.add(_param_name)
            return tuple(sorted(_param_names))

        endpoint_key = (module_name, rel)
        parameter_key = _param_key(path, parameters)
        endpoint_entry = self._endpoints.setdefault(endpoint_key, {})
        if parameter_key in endpoint_entry:
            raise RuntimeError("The endpoint %r has already been set to %r" %
                               (endpoint_key, endpoint_entry[parameter_key]))

        endpoint_entry[parameter_key] = {
            'href': path,
            'method': method,
            'rel': rel,
            'parameters': parameters,
        }


# This registry is used to allow endpoints to link to each other without knowing the exact URL.
ENDPOINT_REGISTRY = EndpointRegistry()


# We reconstruct the URL according to the parameter specification.
def _make_url(
    path: str,
    param_spec: List[PrimitiveParameter],
    param_val: Dict[str, str],
) -> str:
    """Make a concrete URL according to parameter specs and value-mappings.

    Examples:

        For use in path

        >>> _make_url('/foo/{host}', [{'name': 'host', 'in': 'path'}], {'host': 'example.com'})
        '/foo/example.com'

        Or in query-string:

        >>> _make_url('/foo', [{'name': 'host', 'in': 'query'}], {'host': 'example.com'})
        '/foo?host=example.com'

        >>> _make_url('/foo', [{'name': 'host', 'in': 'query', 'required': False}],
        ...           {'host': 'example.com'})
        '/foo?host=example.com'

        >>> _make_url('/foo', [{'name': 'host', 'in': 'query', 'required': False}], {})
        '/foo'

        Some edge-cases which are caught.

        >>> _make_url('/foo', [{'name': 'host', 'in': 'path'}], {})
        Traceback (most recent call last):
        ...
        ValueError: No parameter mapping for required parameter 'host'.

        >>> _make_url('/foo', [{'name': 'host', 'in': 'path'}], {'host': 'example.com'})
        Traceback (most recent call last):
        ...
        ValueError: Parameter 'host' (required path-parameter), not found in path '/foo'

        >>> import pytest
        >>> # This exceptions gets thrown by another function, so we don't care about the wording.
        >>> with pytest.raises(ValueError):
        ...     _make_url('/foo/{host}', [], {'host': 'example.com'})

    Args:
        path:
            The path. May have "{variable_name}" template parts in the path-name or not.

        param_spec:
            A list of parameters.

        param_val:
            A mapping of parameter-names to their desired values. Used to fill out the templates.

    Returns:
        The formatted path, query-string appended if applicable.

    """
    params_in_path = PARAM_RE.findall(path)
    path_params = {}
    qs = []
    for p in param_spec:
        # TODO: Move this de-referencing somewhere usable.
        if isinstance(p, str):
            # Cyclical imports otherwise. :-/
            raise ValueError("Globally defined names not supported.")

        param_name = p['name']
        if param_name not in param_val:
            if p.get('required', True):
                raise ValueError(f"No parameter mapping for required parameter {param_name!r}.")
            # We skip optional parameters, when we don't have values for them.
            continue

        param_value = param_val[param_name]
        if p['in'] == 'query':
            qs.append(f"{param_name}={param_value}")
        elif p['in'] == 'path':
            if param_name not in params_in_path:
                raise ValueError(f"Parameter {param_name!r} (required path-parameter), "
                                 f"not found in path {path!r}")
            path_params[param_name] = {'example': param_value}

    query_string = '&'.join(qs)
    rv = fill_out_path_template(path, path_params)
    if query_string:
        rv += f"?{query_string}"
    return rv
