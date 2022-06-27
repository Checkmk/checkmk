#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains the "Endpoint Registry".

This registry has multiple jobs:

 1. store the endpoint for potential SPEC generation via "make openapi"
 2. interlinking between endpoints without having to know the specific URL.

"""
from typing import Any, Dict, Iterator, List, Sequence

from cmk.gui.plugins.openapi.restful_objects.params import fill_out_path_template, path_parameters
from cmk.gui.plugins.openapi.restful_objects.type_defs import (
    EndpointEntry,
    EndpointKey,
    LinkRelation,
    OpenAPIParameter,
    ParameterKey,
)


# This is the central store for all our endpoints. We use this to determine the correct URLs at
# runtime so that we can't have typos when interlinking responses.
class EndpointRegistry:
    """Registry for endpoints.

    Examples:

        >>> class EndpointWithParams:
        ...      method = 'get'
        ...      path = '/foo/d41d8cd98f/{hostname}'
        ...      func = lambda: None
        ...      link_relation = '.../update'
        ...

        >>> reg = EndpointRegistry()
        >>> reg.add_endpoint(EndpointWithParams,
        ...                  [{'name': "hostname", 'in': 'path'}])

        >>> endpoint = reg.lookup(__name__, ".../update", {'hostname': 'example.com'})
        >>> assert endpoint['href'] == '/foo/d41d8cd98f/example.com', endpoint
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
        ...      link_relation = '.../update'

        >>> reg = EndpointRegistry()
        >>> reg.add_endpoint(EndpointWithoutParams,
        ...     [{'name': 'hostname', 'in': 'query', 'required': True}])

    """

    def __init__(self) -> None:
        self._endpoints: Dict[EndpointKey, Dict[ParameterKey, EndpointEntry]] = {}
        self._endpoint_list: List[EndpointEntry] = []

    def __iter__(self) -> Iterator[Any]:
        return iter(self._endpoint_list)

    def lookup(
        self,
        module_name: str,
        rel: LinkRelation,
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
            raise ValueError(
                f"Endpoint {endpoint_key} with parameters {parameter_key} not found. "
                f"The following parameter combinations are possible: "
                f"{list(endpoint_entry.keys())}"
            )

        examples: Dict[str, OpenAPIParameter] = {
            key: {"example": value} for key, value in parameter_values.items()
        }

        # Needs to fill out path templates!
        entry = endpoint_entry[parameter_key]
        entry["href"] = fill_out_path_template(entry["href"], examples)
        return entry

    def add_endpoint(
        self,
        endpoint,  # not typed due to cyclical imports. need to refactor modules first.
        parameters: Sequence[OpenAPIParameter],
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
                if (
                    "schema" not in _param
                    and isinstance(_param, dict)
                    and _param.get("required", True)
                ):
                    _param_names.add(_param["name"])
            for _param_name in path_parameters(_path):
                _param_names.add(_param_name)
            return tuple(sorted(_param_names))

        endpoint_key = (module_name, endpoint.link_relation)
        parameter_key = _param_key(endpoint.path, parameters)
        endpoint_entry = self._endpoints.setdefault(endpoint_key, {})
        if parameter_key in endpoint_entry:
            raise RuntimeError(
                "The endpoint %r has already been set to %r"
                % (endpoint_key, endpoint_entry[parameter_key])
            )

        endpoint_entry[parameter_key] = {
            "endpoint": endpoint,
            "href": endpoint.path,  # legacy
            "method": endpoint.method,  # legacy
            "rel": endpoint.link_relation,  # legacy
            "parameters": parameters,
        }


def _make_url(
    path: str,
    param_spec: Sequence[OpenAPIParameter],
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
    path_params: Dict[str, OpenAPIParameter] = {}
    qs = []
    for p in param_spec:
        param_name = p["name"]
        if param_name not in param_val:
            if p.get("required", True):
                raise ValueError(f"No parameter mapping for required parameter {param_name!r}.")
            # We skip optional parameters, when we don't have values for them.
            continue

        param_value = param_val[param_name]
        if p["in"] == "query":
            qs.append(f"{param_name}={param_value}")
        elif p["in"] == "path":
            if param_name not in path_parameters(path):
                raise ValueError(
                    f"Parameter {param_name!r} (required path-parameter), "
                    f"not found in path {path!r}"
                )
            path_params[param_name] = {"example": param_value}

    query_string = "&".join(qs)
    rv = fill_out_path_template(path, path_params)
    if query_string:
        rv += f"?{query_string}"
    return rv


# This registry is used to allow endpoints to link to each other without knowing the exact URL.
ENDPOINT_REGISTRY = EndpointRegistry()
