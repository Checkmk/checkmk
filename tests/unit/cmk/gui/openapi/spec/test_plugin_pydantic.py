#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest
from apispec import APISpec

from cmk.gui.openapi._type_adapter import get_cached_type_adapter
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.spec.plugin_pydantic import _get_json_schema, CheckmkPydanticPlugin


@api_model
class Host:
    name: str = api_field(description="The host name.", example="host1")


@api_model
class Service:
    description: str = api_field(description="The service description.", example="CPU load")


@api_model
class Collection[T, D]:
    domainType: D = api_field(description="The domain type.", example="host")
    value: list[T] = api_field(description="The objects in the collection.")


type HostCollection = Collection[Host, Literal["host"]]


@api_model
class Envelope:
    inner: HostCollection = api_field(description="A nested collection.")


@pytest.fixture(name="spec")
def _spec() -> APISpec:
    return APISpec(
        title="Test", version="1.0", openapi_version="3.1.0", plugins=[CheckmkPydanticPlugin()]
    )


def test_model_is_registered_under_its_class_name(spec: APISpec) -> None:
    reference = _get_json_schema(spec, get_cached_type_adapter(Host), "outbound")

    assert reference == {"$ref": "#/components/schemas/Host"}
    assert sorted(spec.components.schemas) == ["Host"]


def test_parameterizations_get_distinct_components(spec: APISpec) -> None:
    """Without an alias, the name pydantic derives keeps the type arguments apart."""
    for type_ in (Collection[Host, Literal["host"]], Collection[Service, Literal["service"]]):
        _get_json_schema(spec, get_cached_type_adapter(type_), "outbound")

    assert sorted(spec.components.schemas) == [
        "Collection_Host_Literal__host___",
        "Collection_Service_Literal__service___",
        "Host",
        "Service",
    ]


def test_alias_names_the_parameterization(spec: APISpec) -> None:
    root = _get_json_schema(spec, get_cached_type_adapter(HostCollection), "outbound")

    assert root == {"$ref": "#/components/schemas/HostCollection"}
    schema = spec.components.schemas["HostCollection"]
    assert schema["properties"]["value"]["items"] == {"$ref": "#/components/schemas/Host"}
    assert schema["properties"]["domainType"]["const"] == "host"


def test_top_level_and_nested_use_share_one_component(spec: APISpec) -> None:
    """The root schema must be named the same way as the same schema nested in another one."""
    root = _get_json_schema(spec, get_cached_type_adapter(HostCollection), "outbound")
    _get_json_schema(spec, get_cached_type_adapter(Envelope), "outbound")

    assert root == {"$ref": "#/components/schemas/HostCollection"}
    assert spec.components.schemas["Envelope"]["properties"]["inner"] == {
        "$ref": "#/components/schemas/HostCollection",
        "description": "A nested collection.",
    }
    assert sorted(spec.components.schemas) == ["Envelope", "Host", "HostCollection"]


def test_union_without_a_definition_is_inlined(spec: APISpec) -> None:
    reference = _get_json_schema(spec, get_cached_type_adapter(Host | Service), "outbound")

    assert reference == {
        "anyOf": [
            {"$ref": "#/components/schemas/Host"},
            {"$ref": "#/components/schemas/Service"},
        ]
    }
    assert sorted(spec.components.schemas) == ["Host", "Service"]
