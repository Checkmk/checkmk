#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator

import pytest

from tests.unit.cmk.gui.openapi.framework.factories import (
    EndpointDocFactory,
    EndpointFamilyFactory,
    EndpointHandlerFactory,
    EndpointMetadataFactory,
    VersionedEndpointFactory,
)

from cmk.gui.openapi import endpoint_family_registry
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry


@pytest.fixture
def endpoint_family() -> Generator[str]:
    """Fixture to register an endpoint family before each test."""
    family = EndpointFamilyFactory.build(name="test_family", doc_group="Setup")
    endpoint_family_registry.register(family, ignore_duplicates=False)
    yield family.name
    endpoint_family_registry.unregister(family.name)


def test_endpoint_definition_family_inherited_doc_group() -> None:
    family_name = "test_family"
    family = EndpointFamilyFactory.build(name=family_name, doc_group="Setup")
    endpoint = VersionedEndpointFactory.build(
        doc=EndpointDocFactory.build(family=family_name, group=None)
    )

    endpoint_definition = VersionedEndpointRegistry.create_endpoint_definition(
        endpoint, family, EndpointHandlerFactory.build()
    )

    assert endpoint_definition.doc_group == "Setup"


def test_endpoint_definition_overwritten_doc_group() -> None:
    family_name = "test_family"
    family = EndpointFamilyFactory.build(name=family_name, doc_group="Setup")
    endpoint = VersionedEndpointFactory.build(
        doc=EndpointDocFactory.build(family=family_name, group="Undocumented Endpoint")
    )

    endpoint_definition = VersionedEndpointRegistry.create_endpoint_definition(
        endpoint, family, EndpointHandlerFactory.build()
    )

    assert endpoint_definition.doc_group == "Undocumented Endpoint"


def test_register_versioned_endpoint(endpoint_family: str) -> None:
    endpoint = VersionedEndpointFactory.build(
        versions={
            APIVersion.V1: EndpointHandlerFactory.build(),
            APIVersion.UNSTABLE: EndpointHandlerFactory.build(),
        },
        doc=EndpointDocFactory.build(family=endpoint_family),
        metadata=EndpointMetadataFactory.build(link_relation="link"),
    )

    test_registry = VersionedEndpointRegistry()
    test_registry.register(endpoint, ignore_duplicates=False)

    endpoint_key = (endpoint_family, endpoint.metadata.link_relation)
    assert len(test_registry._versions) == 2
    assert endpoint_key in test_registry._versions[APIVersion.V1]
    assert endpoint_key in test_registry._versions[APIVersion.UNSTABLE]


def test_invalid_double_registration(endpoint_family: str) -> None:
    endpoint = VersionedEndpointFactory.build(doc=EndpointDocFactory.build(family=endpoint_family))

    test_registry = VersionedEndpointRegistry()
    test_registry.register(endpoint, ignore_duplicates=False)

    with pytest.raises(RuntimeError, match="Endpoint with key"):
        test_registry.register(endpoint, ignore_duplicates=False)
