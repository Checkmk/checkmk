#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator, Mapping
from typing import Annotated
from urllib.parse import parse_qs, urlparse

import pytest

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.framework._types import HeaderParam, PathParam, QueryParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.endpoint_link import (
    EndpointLinkNotFoundError,
    EndpointLinkParameterError,
    link_to_endpoint,
    path_to_endpoint,
)
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.framework.registry import versioned_endpoint_registry
from cmk.gui.openapi.restful_objects.endpoint_family import endpoint_family_registry
from cmk.gui.openapi.restful_objects.type_defs import LinkRelation
from cmk.gui.openapi.versioned_endpoint_map import _discover_endpoints
from tests.unit.cmk.gui.openapi.framework.factories import (
    EndpointDocFactory,
    EndpointFamilyFactory,
    EndpointHandlerFactory,
    EndpointMetadataFactory,
    VersionedEndpointFactory,
)

_FAMILY_NAME = "test_endpoint_link"
_LINK_REL: LinkRelation = "cmk/show"


@pytest.fixture(autouse=True)
def _registry_fixture() -> Generator[None]:
    """Register the family and snapshot/restore the endpoint registry per-test."""
    fam = EndpointFamilyFactory.build(name=_FAMILY_NAME, doc_group="Setup")
    endpoint_family_registry.register(fam)
    original = {v: dict(eps) for v, eps in versioned_endpoint_registry._versions.items()}
    # ``_discover_endpoints`` memoizes its result per process; clear before and
    # after each test so registrations done here cannot leak into unrelated tests.
    _discover_endpoints.cache_clear()  # type: ignore[attr-defined]
    try:
        yield
    finally:
        versioned_endpoint_registry._versions = original
        endpoint_family_registry.unregister(fam.name)
        _discover_endpoints.cache_clear()  # type: ignore[attr-defined]


def _register(
    *version_handlers: tuple[APIVersion, object],
    method: HTTPMethod = "get",
    removed_in_version: APIVersion | None = None,
) -> None:
    """Register a test endpoint with one or more version-specific handlers."""
    versions = {v: EndpointHandlerFactory.build(handler=h) for v, h in version_handlers}
    versioned_endpoint_registry.register(
        VersionedEndpointFactory.build(
            metadata=EndpointMetadataFactory.build(
                path="/objects/test_thing/{thing_id}",
                method=method,
                link_relation=_LINK_REL,
                content_type="application/json",
            ),
            doc=EndpointDocFactory.build(family=_FAMILY_NAME),
            versions=versions,
            removed_in_version=removed_in_version,
        )
    )


def _path(version: APIVersion = APIVersion.V1, **parameters: str) -> str:
    return path_to_endpoint(
        family=_FAMILY_NAME,
        link_relation=_LINK_REL,
        version=version,
        parameters=parameters,
    )


def _link(
    version: APIVersion = APIVersion.V1,
    body: Mapping[str, object] | None = None,
    **parameters: str,
) -> LinkModel:
    return link_to_endpoint(
        family=_FAMILY_NAME,
        link_relation=_LINK_REL,
        version=version,
        host_url="https://example.com/",
        parameters=parameters,
        body=body,
    )


def _handler_with_path_param(
    thing_id: Annotated[str, PathParam(description="Thing ID", example="abc")],
) -> None:
    return None


def _handler_with_path_and_query(
    thing_id: Annotated[str, PathParam(description="Thing ID", example="abc")],
    query_filter: Annotated[
        str | None, QueryParam(alias="filter", description="Filter", example="x")
    ] = None,
    limit: Annotated[str | None, QueryParam(description="Limit", example="5")] = None,
) -> None:
    return None


# -- Path/query classification ----------------------------------------------


def test_path_to_endpoint_fills_path_template() -> None:
    _register((APIVersion.V1, _handler_with_path_param))

    path = _path(thing_id="abc")

    assert path.endswith("/check_mk/api/v1/objects/test_thing/abc")
    assert path.startswith("/")


def test_path_to_endpoint_path_and_query_params() -> None:
    _register((APIVersion.V1, _handler_with_path_and_query))

    path = _path(thing_id="abc", filter="x", limit="5")

    parsed = urlparse(path)
    assert parsed.path.endswith("/objects/test_thing/abc")
    assert parse_qs(parsed.query) == {"filter": ["x"], "limit": ["5"]}


def test_path_to_endpoint_missing_path_param_raises() -> None:
    _register((APIVersion.V1, _handler_with_path_param))

    with pytest.raises(EndpointLinkParameterError, match="Missing path parameters"):
        _path()


def test_path_to_endpoint_unknown_parameter_raises() -> None:
    _register((APIVersion.V1, _handler_with_path_param))

    with pytest.raises(EndpointLinkParameterError, match="Unknown parameter 'bogus'"):
        _path(thing_id="abc", bogus="val")


def test_path_to_endpoint_optional_query_param_omitted() -> None:
    _register((APIVersion.V1, _handler_with_path_and_query))

    path = _path(thing_id="abc")

    parsed = urlparse(path)
    assert parsed.path.endswith("/objects/test_thing/abc")
    assert parsed.query == ""


# -- Handler selection across versions --------------------------------------


def test_path_to_endpoint_inherits_to_newer_version() -> None:
    """An endpoint registered at V1 is inherited into UNSTABLE's endpoint map,
    and the generated URL uses the requested version's prefix."""
    _register((APIVersion.V1, _handler_with_path_param))

    path = _path(version=APIVersion.UNSTABLE, thing_id="abc")

    assert "/check_mk/api/unstable/objects/test_thing/abc" in path


def test_path_to_endpoint_uses_per_version_handler_annotations() -> None:
    """When versions have different handlers, the requested version's handler drives classification."""
    _register(
        (APIVersion.V1, _handler_with_path_param),
        (APIVersion.UNSTABLE, _handler_with_path_and_query),
    )

    # V1's handler has no `filter` parameter → rejected as unknown.
    with pytest.raises(EndpointLinkParameterError, match="Unknown parameter 'filter'"):
        _path(version=APIVersion.V1, thing_id="abc", filter="x")

    # UNSTABLE's handler accepts `filter` as a query param.
    path = _path(version=APIVersion.UNSTABLE, thing_id="abc", filter="x")
    parsed = urlparse(path)
    assert "/check_mk/api/unstable/objects/test_thing/abc" in parsed.path
    assert parse_qs(parsed.query) == {"filter": ["x"]}


def test_path_to_endpoint_not_registered_raises() -> None:
    with pytest.raises(EndpointLinkNotFoundError):
        _path(thing_id="abc")


# -- Header parameters -------------------------------------------------------


def _handler_with_required_header(
    thing_id: Annotated[str, PathParam(description="Thing ID", example="abc")],
    x_custom: Annotated[str, HeaderParam(description="Custom header", example="val")],
) -> None:
    return None


def test_path_to_endpoint_required_header_raises() -> None:
    _register((APIVersion.V1, _handler_with_required_header))

    with pytest.raises(EndpointLinkParameterError, match="header parameters"):
        _path(thing_id="abc")


def _handler_with_optional_header(
    thing_id: Annotated[str, PathParam(description="Thing ID", example="abc")],
    x_custom: Annotated[str, HeaderParam(description="Custom header", example="val")] = "default",
) -> None:
    return None


def test_path_to_endpoint_optional_header_allowed() -> None:
    _register((APIVersion.V1, _handler_with_optional_header))

    path = _path(thing_id="abc")

    assert path.endswith("/check_mk/api/v1/objects/test_thing/abc")


# -- Body parameters ---------------------------------------------------------


def _handler_with_body(
    thing_id: Annotated[str, PathParam(description="Thing ID", example="abc")],
    body: dict[str, str | int],
) -> None:
    return None


def test_path_to_endpoint_raises_when_body_expected() -> None:
    _register((APIVersion.V1, _handler_with_body), method="post")

    with pytest.raises(EndpointLinkParameterError, match="request body"):
        _path(thing_id="abc")


def test_link_to_endpoint_missing_body_for_body_endpoint_raises() -> None:
    _register((APIVersion.V1, _handler_with_body), method="post")

    with pytest.raises(EndpointLinkParameterError, match="requires a request body"):
        _link(thing_id="abc")


def test_link_to_endpoint_body_on_no_body_endpoint_raises() -> None:
    _register((APIVersion.V1, _handler_with_path_param))

    with pytest.raises(EndpointLinkParameterError, match="does not accept a request body"):
        _link(thing_id="abc", body={"field1": "value1"})


def test_link_to_endpoint_includes_body_params() -> None:
    _register((APIVersion.V1, _handler_with_body), method="post")

    link = _link(thing_id="abc", body={"field1": "value1", "field2": 42})

    assert link.body_params == {"field1": "value1", "field2": 42}


# -- LinkModel construction --------------------------------------------------


def test_link_to_endpoint_returns_link_model() -> None:
    _register((APIVersion.V1, _handler_with_path_param), method="post")

    link = _link(thing_id="abc")

    parsed = urlparse(link.href)
    assert parsed.path.endswith("/check_mk/api/v1/objects/test_thing/abc")
    assert link.method == "POST"
    assert link.rel == _LINK_REL
    assert link.type == "application/json"
    assert link.domainType == "link"
