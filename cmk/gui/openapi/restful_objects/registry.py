#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains the "Endpoint Registry".

This registry does interlinking between endpoints without having to know the specific URL.

"""

from collections.abc import Iterator
from typing import TypedDict

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.restful_objects.decorators import Endpoint, WrappedEndpoint
from cmk.gui.openapi.restful_objects.params import fill_out_path_template, path_parameters
from cmk.gui.openapi.restful_objects.type_defs import (
    EndpointKey,
    LinkRelation,
    OpenAPIParameter,
    ParameterKey,
)


class EndpointEntry(TypedDict, total=True):
    endpoint: Endpoint
    href: str
    method: HTTPMethod
    rel: LinkRelation


# This is the central store for all our endpoints. We use this to determine the correct URLs at
# runtime so that we can't have typos when interlinking responses.
class EndpointRegistry:
    """Registry for endpoints.

    Examples:

        >>> class Endpoint:
        ...      method = 'get'
        ...      path = '/foo/d41d8cd98f/{hostname}'
        ...      func = lambda: None
        ...      link_relation = '.../update'
        ...

        >>> class WrappedEndpoint:
        ...      endpoint = Endpoint
        ...

        >>> reg = EndpointRegistry()
        >>> reg.register(WrappedEndpoint, ignore_duplicates=False)
        >>> endpoint = reg.lookup(__name__, ".../update", {'hostname': 'example.com'})
        >>> assert endpoint['href'] == '/foo/d41d8cd98f/example.com', endpoint
        >>> assert endpoint['method'] == 'get'
        >>> assert endpoint['rel'] == '.../update'
        >>> assert endpoint['endpoint'] == Endpoint, endpoint['endpoint']

        >>> reg.lookup(__name__, ".../update", {})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: ...
    """

    def __init__(self) -> None:
        self._endpoints: dict[EndpointKey, dict[ParameterKey, EndpointEntry]] = {}
        self._endpoint_list: list[Endpoint] = []
        self.ignore_duplicates: bool = False

    def __iter__(self) -> Iterator[Endpoint]:
        return iter(self._endpoint_list)

    def lookup(
        self,
        module_name: str,
        rel: LinkRelation,
        parameter_values: dict[str, str],
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

        examples: dict[str, OpenAPIParameter] = {
            key: {"example": value} for key, value in parameter_values.items()
        }

        # Needs to fill out path templates!
        entry = endpoint_entry[parameter_key]
        entry["href"] = fill_out_path_template(entry["href"], examples)
        return entry

    def register(self, wrapped_endpoint: WrappedEndpoint, *, ignore_duplicates: bool) -> None:
        endpoint = wrapped_endpoint.endpoint
        self._endpoint_list.append(endpoint)
        func = endpoint.func
        module_name = func.__module__

        endpoint_key = (module_name, endpoint.link_relation)
        parameter_key = tuple(sorted(path_parameters(endpoint.path)))
        endpoint_entry = self._endpoints.setdefault(endpoint_key, {})
        if parameter_key in endpoint_entry:
            if ignore_duplicates:
                return

            raise RuntimeError(
                f"The endpoint {endpoint_key!r} has already been set to {endpoint_entry[parameter_key]!r}"
            )

        endpoint_entry[parameter_key] = {
            "endpoint": endpoint,
            "href": endpoint.path,  # legacy
            "method": endpoint.method,  # legacy
            "rel": endpoint.link_relation,  # legacy
        }

    def unregister(self, wrapped_endpoint: WrappedEndpoint) -> None:
        """
        Removes an endpoint. This is currently only used in tests.
        The implementation is not optimized for performance.
        """
        endpoint = wrapped_endpoint.endpoint
        self._endpoint_list.remove(endpoint)
        parameter_key = None
        endpoint_key = None
        for e_key, e_value in self._endpoints.items():
            for p_key, p_value in e_value.items():
                if p_value["endpoint"] == endpoint:
                    parameter_key = p_key
                    endpoint_key = e_key
        if parameter_key is None or endpoint_key is None:
            raise ValueError(f"Could not find endpoint {endpoint}")
        self._endpoints[endpoint_key].pop(parameter_key)


# This registry is used to allow endpoints to link to each other without knowing the exact URL.
endpoint_registry = EndpointRegistry()
