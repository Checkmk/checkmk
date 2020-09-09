#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypedDict,
    Union,
)

from marshmallow import Schema  # type: ignore[import]

from cmk.gui.plugins.openapi.restful_objects.datastructures import denilled
from cmk.gui.plugins.openapi.restful_objects.params import PARAM_RE, path_parameters

DomainType = Literal[
    'agent',
    'activation_run',
    'bi_rule',
    'bi_aggregation',
    'bi_pack',
    'contact_group_config',
    'folder_config',
    'downtime',
    'host',
    'hostgroup',
    'host_config',
    'host_group_config',
    'password',
    'service',
    'servicegroup',
    'service_discovery',
    'service_group_config',
    'time_period',
    'user',
]  # yapf: disable

DomainObject = Dict[str, Any]

CmkEndpointName = Literal[
    'cmk/run',
    'cmk/activate',
    'cmk/bake',
    'cmk/bake_and_sign',
    'cmk/cancel',
    'cmk/bulk_create',
    'cmk/bulk_update',
    'cmk/create',
    'cmk/download',
    'cmk/list',
    'cmk/move',
    'cmk/show',
    'cmk/sign',
    'cmk/start',
    'cmk/put_bi_rule',
    'cmk/put_bi_aggregation',
    'cmk/put_bi_pack',
    'cmk/put_bi_packs',
    'cmk/get_bi_rule',
    'cmk/get_bi_aggregation',
    'cmk/get_bi_pack',
    'cmk/get_bi_packs',
    'cmk/wait-for-completion',
    'cmk/baking-status',
    'cmk/bakery-status',
    'cmk/service.move-monitored',
    'cmk/service.move-undecided',
    'cmk/service.move-ignored',
    'cmk/service.bulk-acknowledge',
]  # yapf: disable

RestfulEndpointName = Literal[
    "describedby",  # sic
    "help",
    "icon",
    "previous",
    "next",
    "self",
    "up",
    ".../action",
    ".../action-param",
    ".../add-to",  # takes params
    ".../attachment",  # takes params
    ".../choice",  # takes params
    ".../clear",
    ".../collection",
    ".../default",
    ".../delete",
    ".../details",  # takes params
    ".../domain-type",
    ".../domain-types",
    ".../element",
    ".../element-type",
    ".../invoke",
    ".../modify",
    ".../persist",
    ".../property",
    ".../remove-from",  # takes params
    ".../return-type",
    ".../services",
    ".../service",  # takes params
    ".../update",
    ".../user",
    ".../value",  # takes params
    ".../version",
]  # yapf: disable

EndpointName = Union[CmkEndpointName, RestfulEndpointName]

HTTPMethod = Literal["get", "put", "post", "delete"]

PropertyFormat = Literal[
    # String values
    'string',
    # The value should simply be interpreted as a string. This is also the default if
    # the "format" json-property is omitted (or if no domain metadata is available)
    'date-time',  # A date in ISO 8601 format of YYYY-MM-DDThh:mm:ssZ in UTC time
    'date',  # A date in the format of YYYY-MM-DD.
    'time',  # A time in the format of hh:mm:ss.
    'utc-millisec',  # The difference, measured in milliseconds, between the
    # specified time and midnight, 00:00 of January 1, 1970 UTC.
    'big-integer(n)',  # The value should be parsed as an integer, scale n.
    'big-integer(s,p)',  # The value should be parsed as a big decimal, scale n,
    # precision p.
    'blob',  # base-64 encoded byte-sequence
    'clob',  # character large object: the string is a large array of
    # characters, for example an HTML resource
    # Non-string values
    'decimal',  # the number should be interpreted as a float-point decimal.
    'int',  # the number should be interpreted as an integer.
]  # yapf: disable
CollectionItem = Dict[str, str]
LocationType = Literal['path', 'query', 'header', 'cookie']
ResultType = Literal["object", "list", "scalar", "void"]
LinkType = Dict[str, str]
CollectionObject = TypedDict('CollectionObject', {
    'id': str,
    'domainType': str,
    'links': List[LinkType],
    'value': Any,
    'extensions': Dict[str, str]
})
Serializable = Union[Dict[str, Any], CollectionObject]  # because TypedDict is stricter
ETagBehaviour = Literal["input", "output", "both"]

SchemaClass = Type[Schema]
SchemaInstanceOrClass = Union[Schema, SchemaClass]
ResponseSchema = Optional[SchemaInstanceOrClass]
RequestSchema = Optional[SchemaInstanceOrClass]
OpenAPISchemaType = Literal['string', 'array', 'object', 'boolean', 'integer', 'number']


def _translate_to_openapi_keys(
    name: Optional[str] = None,
    location: Optional[LocationType] = None,
    description: Optional[str] = None,
    required: Optional[bool] = None,
    example: Optional[str] = None,
    allow_emtpy: Optional[bool] = None,
    schema_enum: Optional[List[str]] = None,
    schema_type: Optional[OpenAPISchemaType] = None,
    schema_string_pattern: Optional[str] = None,
    schema_string_format: Optional[str] = None,
    schema_num_minimum: Optional[int] = None,
    schema_num_maximum: Optional[int] = None,
):
    schema: Dict[str, Any] = {'type': schema_type}
    if schema_type == 'string':
        schema.update(
            format=schema_string_format,
            pattern=schema_string_pattern,
        )
    if schema_enum:
        schema.update(enum=schema_enum,)
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
        'schema': denilled(schema) or None,
    }
    return raw_values


ValidatorType = Callable[[Any], Optional[Dict[str, List[str]]]]


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
        super(ParamDict, self).__init__(*seq, **kwargs)

    def __call__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[LocationType] = None,
        required: Optional[bool] = None,
        allow_empty: Optional[bool] = None,
        example: Optional[str] = None,
        schema_type: Optional[OpenAPISchemaType] = None,
        schema_string_pattern: Optional[str] = None,
        schema_string_format: Optional[str] = None,
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
        new_dict.update(denilled(raw_values))
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
        example: Optional[str] = None,
        schema_enum: Optional[List[str]] = None,
        schema_type: Optional[OpenAPISchemaType] = 'string',
        schema_string_pattern: Optional[str] = None,
        schema_string_format: Optional[str] = None,
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

            schema_enum:
                A list of distinct values that this parameter can hold. These will be rendered in
                the documentation as well.

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
            schema_enum=schema_enum,
            schema_num_maximum=schema_num_maximum,
            schema_num_minimum=schema_num_minimum,
            schema_string_format=schema_string_format,
            schema_string_pattern=schema_string_pattern,
        )
        # We throw away None valued keys so they won't show up in the specification.
        return cls(denilled(raw_values))

    def to_dict(self):
        return dict(self)

    def spec_tuple(self):
        """Return a tuple suitable for passing into components.parameters()"""
        new = self()
        return new.pop('name'), new.pop('in'), new.to_dict()

    def header_dict(self) -> Dict[str, 'PrimitiveParameter']:
        new = self()
        location = new.pop('in')
        if location != 'header':
            raise ValueError("Only header parameters can be added to the header-struct.")
        return {new.pop('name'): new.to_dict()}


Parameter = ParamDict
SchemaType = TypedDict(
    "SchemaType",
    {
        'type': OpenAPISchemaType,
        'format': PropertyFormat,
        'pattern': str,
    },
    total=False,
)
PrimitiveParameter = TypedDict(
    "PrimitiveParameter",
    {
        'name': str,
        'in': LocationType,
        'required': bool,
        'allowEmptyValue': bool,
        'example': Any,
        'schema': SchemaType,
    },
    total=False,
)
ParameterReference = str
AnyParameter = Union[Parameter, PrimitiveParameter]
AnyParameterAndReference = Union[Parameter, PrimitiveParameter, ParameterReference]

PathItem = TypedDict(
    "PathItem",
    {
        'content': Dict[str, Dict[str, Any]],
        'description': str,
        'headers': Dict[str, PrimitiveParameter],
    },
    total=False,
)

ResponseType = TypedDict("ResponseType", {
    "default": PathItem,
    "200": PathItem,
    "204": PathItem,
    "301": PathItem,
    "302": PathItem,
},
                         total=False)

OperationSpecType = TypedDict(
    "OperationSpecType",
    {
        'x-codeSamples': List[Dict[str, str]],
        'operationId': str,
        'tags': List[str],
        'description': str,
        'responses': ResponseType,
        'parameters': List[Union[PrimitiveParameter, ParameterReference]],
        'requestBody': Dict[str, Any],
        'summary': str,
    },
    total=False,
)

OpenAPITag = TypedDict(
    "OpenAPITag",
    {
        'name': str,
        'description': str,
        'externalDocs': str,
        'x-displayName': str,
    },
    total=False,
)


def fill_out_path_template(
    orig_path: str,
    parameters: Dict[str, PrimitiveParameter],
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
            raise ValueError(f"Parameter {path_param!r} needed, but not supplied.")

        param_spec = parameters[path_param]
        if 'example' not in param_spec:
            raise ValueError(f"Parameter {path_param!r} of path {orig_path!r} has no example.")

        path = path.replace("{" + path_param + "}", param_spec['example'])
    return path


EndpointEntry = TypedDict(
    "EndpointEntry",
    {
        'endpoint': Any,
        'href': str,
        'method': HTTPMethod,
        'rel': EndpointName,
        'parameters': Sequence[PrimitiveParameter],
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

        >>> class EndpointWithParams:
        ...      method = 'get'
        ...      path = '/foo/d41d8cd98f/{hostname}'
        ...      func = lambda: None
        ...      name = '.../update'
        ...

        >>> reg = EndpointRegistry()
        >>> reg.add_endpoint(EndpointWithParams,
        ...                  [{'name': "hostname", 'in': 'path'}])

        >>> endpoint = reg.lookup(__name__, ".../update", {'hostname': 'example.com'})
        >>> assert endpoint['href'] == '/foo/d41d8cd98f/example.com'
        >>> assert endpoint['method'] == 'get'
        >>> assert endpoint['rel'] == '.../update'
        >>> assert endpoint['parameters'] == [{'name': 'hostname', 'in': 'path'}]
        >>> assert endpoint['endpoint'] == EndpointWithParams, endpoint['endpoint']

        >>> reg.lookup(__name__, ".../update", {})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: ...

        >>> class EndpointWithoutParams:
        ...      method = 'get'
        ...      path = '/foo'
        ...      func = lambda: None
        ...      name = '.../update'

        >>> reg = EndpointRegistry()
        >>> reg.add_endpoint(EndpointWithoutParams,
        ...     [{'name': 'hostname', 'in': 'query', 'required': True}])

    """
    def __init__(self):
        self._endpoints: Dict[EndpointKey, Dict[ParameterKey, EndpointEntry]] = {}
        self._endpoint_list: List[EndpointEntry] = []

    def __iter__(self) -> Iterator[Any]:
        return iter(self._endpoint_list)

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
        try:
            endpoint_entry = self._endpoints[endpoint_key]
        except KeyError:
            raise KeyError(f"Key {endpoint_key!r} not in {self._endpoints!r}")
        if parameter_key not in endpoint_entry:
            raise ValueError(f"Endpoint {endpoint_key} with parameters {parameter_key} not found. "
                             f"The following parameter combinations are possible: "
                             f"{list(endpoint_entry.keys())}")

        endpoint = endpoint_entry[parameter_key].copy()
        endpoint['href'] = _make_url(endpoint['href'], endpoint['parameters'], parameter_values)
        return endpoint

    def add_endpoint(
        self,
        endpoint,  # not typed due to cyclical imports. need to refactor modules first.
        parameters: Sequence[PrimitiveParameter],
    ) -> None:
        """Adds an endpoint to the registry

        Args:
            endpoint:
                The function or
            parameters:
                The parameters as a list of dicts or strings.

        """
        self._endpoint_list.append(endpoint)
        func = endpoint.func
        module_name = func.__module__

        def _param_key(_path, _parameters):
            # We key on _all_ required parameters, regardless their type.
            _param_names = set()
            for _param in _parameters:
                if isinstance(_param, dict) and _param.get('required', True):
                    _param_names.add(_param['name'])
            for _param_name in path_parameters(_path):
                _param_names.add(_param_name)
            return tuple(sorted(_param_names))

        endpoint_key = (module_name, endpoint.name)
        parameter_key = _param_key(endpoint.path, parameters)
        endpoint_entry = self._endpoints.setdefault(endpoint_key, {})
        if parameter_key in endpoint_entry:
            raise RuntimeError("The endpoint %r has already been set to %r" %
                               (endpoint_key, endpoint_entry[parameter_key]))

        endpoint_entry[parameter_key] = {
            'endpoint': endpoint,
            'href': endpoint.path,  # legacy
            'method': endpoint.method,  # legacy
            'rel': endpoint.name,  # legacy
            'parameters': parameters,
        }


# This registry is used to allow endpoints to link to each other without knowing the exact URL.
ENDPOINT_REGISTRY = EndpointRegistry()


# We reconstruct the URL according to the parameter specification.
def _make_url(
    path: str,
    param_spec: Sequence[PrimitiveParameter],
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
    path_params: Dict[str, PrimitiveParameter] = {}
    qs = []
    for p in param_spec:
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
            if param_name not in path_parameters(path):
                raise ValueError(f"Parameter {param_name!r} (required path-parameter), "
                                 f"not found in path {path!r}")
            path_params[param_name] = {'example': param_value}

    query_string = '&'.join(qs)
    rv = fill_out_path_template(path, path_params)
    if query_string:
        rv += f"?{query_string}"
    return rv
