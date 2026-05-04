#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from cmk.gui.http import Response
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.disabled_endpoint import disabled_versioned
from cmk.gui.openapi.framework.registry import versioned_endpoint_registry
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.decorators import Endpoint, WrappedEndpoint
from cmk.gui.openapi.restful_objects.disabled_endpoint import disabled_legacy
from cmk.gui.openapi.restful_objects.registry import endpoint_registry
from tests.testlib.rest_api_client import ClientRegistry

_DETAIL = "The Agent bakery is not available with your license"


@pytest.fixture(name="disabled_legacy_stub")
def create_disabled_legacy_stub(fresh_app_instance: None) -> Iterator[WrappedEndpoint]:
    @Endpoint(
        path="/test-disabled-legacy-stub",
        method="get",
        link_relation="cmk/test-disabled-legacy-stub",  # type: ignore[arg-type]
        output_empty=True,
        tag_group="Monitoring",
        update_config_generation=False,
        skip_locking=True,
    )
    def _real(param: Mapping[str, Any]) -> Response:
        return Response(status=204)

    stub = disabled_legacy(_real, _DETAIL)
    endpoint_registry.register(stub)
    yield stub
    endpoint_registry.unregister(stub)


@pytest.fixture(name="disabled_versioned_stub")
def create_disabled_versioned_stub(fresh_app_instance: None) -> Iterator[VersionedEndpoint]:
    def _real() -> None:
        return None

    original = VersionedEndpoint(
        metadata=EndpointMetadata(
            path="/test-disabled-versioned-stub",
            link_relation="cmk/test-disabled-versioned-stub",  # type: ignore[arg-type]
            method="get",
        ),
        permissions=EndpointPermissions(),
        doc=EndpointDoc(family="Agents"),
        versions={APIVersion.V1: EndpointHandler(handler=_real)},
        behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    )
    stub = disabled_versioned(original, _DETAIL)
    versioned_endpoint_registry.register(stub)
    yield stub
    versioned_endpoint_registry.unregister(stub)


def test_disabled_legacy_stub_returns_403(
    disabled_legacy_stub: WrappedEndpoint,
    clients: ClientRegistry,
) -> None:
    resp = clients.DisabledEndpointStub.get_legacy(expect_ok=False)
    resp.assert_status_code(403)
    assert resp.json["title"] == "Feature not available"
    assert resp.json["detail"] == _DETAIL
    assert resp.json["status"] == 403


def test_disabled_versioned_stub_returns_403(
    disabled_versioned_stub: VersionedEndpoint,
    clients: ClientRegistry,
) -> None:
    resp = clients.DisabledEndpointStub.get_versioned(expect_ok=False)
    resp.assert_status_code(403)
    assert resp.json["title"] == "Feature not available"
    assert resp.json["detail"] == _DETAIL
    assert resp.json["status"] == 403
